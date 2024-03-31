# panels/kp_panel.py
import tkinter as tk
import numpy as np
from scipy.spatial import Delaunay
import triangle
from .utils import triangles_overlap


class Vertex:
    def __init__(self, x, y, id):
        self.id = id  # vertice of outer triangle have ids 0, 1, 2, each user created vertex id starts from 3
        self.x = x
        self.y = y
        self.degree = 0
        self.adjacent_vertices = set()
        self.triangles = set()
    
    def get_coordinates(self):
        return (self.x, self.y)

    # bi-directional addition(double update)
    def add_adjacent_vertex(self, vertex):
        self.adjacent_vertices.add(vertex)
        vertex.adjacent_vertices.add(self)
        self.degree = len(self.adjacent_vertices)
        vertex.degree = len(vertex.adjacent_vertices)

    def add_triangle(self, triangle):
        self.triangles.add(triangle)
    
    def clear(self):
        self.adjacent_vertices.clear()
        self.triangles.clear()


class TriangleNode:
    _id_counter = 0
    def __init__(self, vertices, is_inside=False, is_leaf=False, is_root=False):
        TriangleNode._id_counter += 1
        self.id = TriangleNode._id_counter
        self.vertices = vertices  # The vertices of the triangle
        self.is_inside = is_inside  # True if the triangle is part of the inner polygon
        self.is_leaf = is_leaf
        self.is_active = True
        self.is_root = is_root
        self.children = set()  # Children in the DAG
        
        # Update vertices' triangles
        for vertex in self.vertices:
            vertex.add_triangle(self)
    
    def add_child(self, child):
        self.children.add(child)
    
    # triangle is removed
    def deactivate(self):
        self.is_active = False
    
    def clear(self):
        self.vertices = []
        self.children.clear()


class KPPanel(tk.Canvas):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.vertices = {}
        self.segments = []
        self.inside_triangles = [] # list of leaf triangles inside the poly
        self.outside_triangles = [] # list of leaf triangles outside the poly
        self.outer_triangle = None # outer bounding triangle vertices
        self.active_triangles = {}
        self.all_triangles = {}
        self.newly_removed_triangles_list = []
        self.newly_added_triangles_list = []
        self.indep_set = set()
        self.focus_set()
        self.bind("<Button-1>", self.mouse_pressed)
        self.bind("<Button-3>", self.mouse_pressed_right)

    def get_active_triangles(self):
        return self.active_triangles

    def mouse_pressed(self, event):
        if self.app.phase == "DRAW":
            vertex_id = len(self.vertices) + 3
            new_vertex = Vertex(event.x, event.y, vertex_id)
            self.vertices[new_vertex.id] = new_vertex
            print(f"[{new_vertex.id}] ({new_vertex.x}, {new_vertex.y}) ")
            self.refresh()
        if self.app.phase == "SEARCH":
            self.delete("all")
            self.create_oval(event.x - 3, event.y - 3, event.x + 3, event.y + 3, fill="black")
            is_in = self.app.dag_panel.point_location((event.x, event.y))
            self.app.dag_panel.draw_search_result(is_in, (event.x, event.y))
            # Draw the point
            color = "green" if is_in else "red"
            self.create_oval(event.x - 3, event.y - 3, event.x + 3, event.y + 3, fill=color, outline=color)

    def mouse_pressed_right(self, event):
        if self.app.phase == "DRAW" and self.vertices:
            last_id = max(self.vertices.keys())
            self.vertices.pop(last_id)
            self.refresh()

    def refresh(self):
        if self.app.phase == "DRAW":
            self.delete("all")
            self.draw_vertices()
            if len(self.vertices.keys()) >= 3:
                self.draw_polygon()
        if self.app.phase == "TRI":
            self.delete("all")
            self.draw_vertices()
            if len(self.vertices.keys()) >= 3:
                self.draw_polygon()
                self.construct_outer_triangle()
                self.draw_outer_triangle_step_by_step()
                self.triangulate_inside_polygon()
                self.after(1200, lambda: self.draw_triangulated_mesh(self.inside_triangles))
                self.triangulate_outer_triangle()
                self.after(2000, lambda: self.draw_triangulated_mesh())
                self.after(2500, lambda: self.app.dag_panel.draw_layer(self.inside_triangles + self.outside_triangles))              
        if self.app.phase == "FIND":
            self.indep_set = self.find_independent_set()
            self.highlight_independent_set(self.indep_set)
        if self.app.phase == "REMOVE":
            self.delete("all")
            self.remove_independent_set(self.indep_set)
            self.draw_triangulated_mesh()
        if self.app.phase == "SEARCH":
            self.delete("all")
            w = self.winfo_reqwidth()
            h = self.winfo_reqheight()
            text_id = self.create_text(w / 2, h / 2 , text="Point Location Time!", fill="#4eaeed", font=("Arial", 14, "bold"))
            self.after(1500, lambda: self.delete(text_id))

                
    def draw_vertices(self):
        for vertex in self.vertices.values():
            self.create_oval(vertex.x - 3, vertex.y - 3, vertex.x + 3, vertex.y + 3, fill="black")

    def draw_polygon(self):
        # Extract (x, y) coordinates from Vertex instances for drawing
        points = [coord for vertex in self.vertices.values() for coord in (vertex.x, vertex.y)]
        self.create_polygon(points, fill="#ede1f7", width=2, outline="blue")

        
    def construct_outer_triangle(self):
        # Convert vertices to a NumPy array for easier manipulation
        vertices = np.array([(vertex.x, vertex.y) for vertex in self.vertices.values()])

        # Find the indices of the top and bottom vertices
        top_index = np.argmax(vertices[:, 1])
        bottom_index = np.argmin(vertices[:, 1])

        # Determine the top vertex and its coordinates
        top_vertex = vertices[top_index]
        top_x, top_y = top_vertex[0], top_vertex[1] + 80

        # Calculate angles of vertices with respect to the top vertex
        angles = np.arctan2(vertices[:, 1] - top_y, vertices[:, 0] - top_x)

        # Sort vertices based on their angles
        sorted_indices = np.argsort(angles)

        # Determine left and right vertices of the outer triangle
        left_index = sorted_indices[0]
        right_index = sorted_indices[-1]
        left_vertex = vertices[left_index]
        right_vertex = vertices[right_index]

        # Calculate slopes of the left and right sides of the outer triangle
        slope_l = (left_vertex[0] - 30 - top_x) / (top_y - left_vertex[1])
        slope_r = (right_vertex[0] + 30 - top_x) / (top_y - right_vertex[1])

        # Calculate coordinates of the left and right vertices
        left_x = int(top_x + slope_l * (top_y - vertices[bottom_index][1] + 30))
        left_y = vertices[bottom_index][1] - 30
        right_x = int(top_x + slope_r * (top_y - vertices[bottom_index][1] + 30))
        right_y = vertices[bottom_index][1] - 30

        # Create the outer triangle as a list of tuples
        self.outer_triangle = [Vertex(top_x, top_y, 0), Vertex(left_x, left_y, 1), Vertex(right_x, right_y, 2)]
        # self.create_polygon([x for point in self.outer_triangle for x in point], fill="", outline="red")
        
    def draw_outer_triangle_step_by_step(self):
        if not self.outer_triangle:
            return
        self.after(250, lambda: self.draw_edge(self.outer_triangle[0].get_coordinates(), self.outer_triangle[1].get_coordinates(), "red"))
        self.after(500, lambda: self.draw_edge(self.outer_triangle[1].get_coordinates(), self.outer_triangle[2].get_coordinates(), "red"))
        self.after(750, lambda: self.draw_edge(self.outer_triangle[2].get_coordinates(), self.outer_triangle[0].get_coordinates(), "red"))

    def draw_edge(self, start, end, color):
        self.create_line(start[0], start[1], end[0], end[1], fill=color, width=2)


    def vertices_to_segments(self, vertices):
        """Convert a list of vertices into a list of line segments."""
        num_vertices = len(vertices)
        for i in range(num_vertices):
            # Connect each vertex to the next, wrapping around to the first
            segment = (vertices[i], vertices[(i + 1) % num_vertices])
            self.segments.append(segment)
            
            
    def process_triangulation_results(self, vertices, triangulated, is_inside, is_leaf):
        new_triangles = {}

        # Iterate over the triangulation results to create TriangleNodes
        for tri_indices in triangulated['triangles']:
            # tri_vertices = [self.vertices[i + 3] for i in tri_indices]
            # all_vertices = self.outer_triangle + list((self.vertices.values()))
            tri_vertices = [vertices[i] for i in tri_indices]
                
            new_triangle = TriangleNode(tri_vertices, is_inside=is_inside, is_leaf=is_leaf)
            new_triangles[new_triangle.id] = new_triangle
            if is_leaf:
                # If leaf, also update inside_triangles and outside_triangles
                if is_inside:
                    self.inside_triangles.append(new_triangle)
                else:
                    self.outside_triangles.append(new_triangle)
            # Update vertex's adjacent set and triangle associations
            for vertex in tri_vertices:
                vertex.add_triangle(new_triangle)
                for adj_vertex in tri_vertices:
                    if vertex != adj_vertex:
                        vertex.add_adjacent_vertex(adj_vertex)

        # Update the active_triangles dictionary
        self.active_triangles.update(new_triangles)
        self.all_triangles.update(new_triangles)
        self.newly_added_triangles_list = list(new_triangles.values())

                

    def triangulate_inside_polygon(self):
        self.inside_triangles.clear()
        num_vertices = len(self.vertices)
        vertices_list = list(self.vertices.values())
        vertices_array = np.array([[vertex.x, vertex.y] for vertex in vertices_list])
        hole_poly = {
            'vertices': vertices_array,
            'segments': [[i, (i + 1) % num_vertices] for i in range(num_vertices)], 
        }
        inner_triangulated = triangle.triangulate(hole_poly, 'p')
        print("inner_triangulated", inner_triangulated)
        
        self.process_triangulation_results(vertices_list, inner_triangulated, is_inside=True, is_leaf=True)
        

    def triangulate_outer_triangle(self):
        self.outside_triangles.clear()
        all_vertices  = self.outer_triangle + list(self.vertices.values())
        vertices_array = np.array([(vertex.x, vertex.y) for vertex in all_vertices])
        outer_segments = [[i, i + 1] for i in range(len(self.outer_triangle) - 1)] + [[len(self.outer_triangle) - 1, 0]]
        inner_segments_start_index = len(self.outer_triangle)
        inner_segments = [[i + inner_segments_start_index, i + 1 + inner_segments_start_index] for i in range(len(self.vertices.keys()) - 1)] + [[inner_segments_start_index + len(self.vertices.keys()) - 1, inner_segments_start_index]]
        
        hole_point = [self.calculate_centroid(self.inside_triangles[0].vertices)]
        hole_poly = {
            'vertices': vertices_array,
            'segments': outer_segments + inner_segments,
            'holes': hole_point
        }
        triangulated = triangle.triangulate(hole_poly, 'p')
        print("triangulated",triangulated)
        self.process_triangulation_results(all_vertices, triangulated, is_inside=False, is_leaf=True)

        for v in (all_vertices):
            print(v.id, "adjacent_vertices", [adj.id for adj in v.adjacent_vertices], "faces:", [tri.id for tri in v.triangles])

        
    def draw_triangulated_mesh(self, given_triangles=None):
        if not given_triangles:
            given_triangles = self.active_triangles.values()
            
        print("active_triangles", [tri.id for tri in given_triangles])
        for triangle in given_triangles:
            # Flatten the list of vertices for the `create_polygon`
            points = [(vertex.x, vertex.y) for vertex in triangle.vertices]
            flat_points = [coord for point in points for coord in point]
            
            fill_color = "#ede1f7" if triangle.is_inside else ""
            outline_color = "black"
            self.create_polygon(flat_points, outline=outline_color, fill=fill_color, width=1.5)
            centroid = self.calculate_centroid(triangle.vertices)
            # Draw a circle at the centroid
            radius = 10  # Radius of the circle, adjust as needed
            fill_color = "white"
            if triangle.is_leaf:
                fill_color = "#9af5b4" if triangle.is_inside else "#f5dd9a"
            self.create_oval(centroid[0] - radius, centroid[1] - radius, centroid[0] + radius, centroid[1] + radius, fill=fill_color)
        
            # Draw the ID number inside the circle
            self.create_text(centroid[0], centroid[1], text=str(triangle.id), font=("Arial", 12))

    def calculate_centroid(self, vertices):
        x = [vertex.x for vertex in vertices]
        y = [vertex.y for vertex in vertices]
        centroid = (sum(x) / len(vertices), sum(y) / len(vertices))
        return centroid

    def find_independent_set(self):
        independent_set = set() 
        considered = set()  # Keep track of vertices id marked as considered
        
        for vertex in self.vertices.values():
            if not vertex.id in considered and vertex.degree < 12:
                independent_set.add(vertex)
                considered.add(vertex.id)  # Mark this vertex as considered
                # mark all adjacent vertices as considered to prevent their addition
                considered.update(adj_vertex.id for adj_vertex in vertex.adjacent_vertices)

        return independent_set
    
    def highlight_independent_set(self, independent_vertices):
        for vertex in independent_vertices:
            self.create_oval(vertex.x - 5, vertex.y - 5, vertex.x + 5, vertex.y + 5, fill="red")

    def remove_independent_set(self, independent_set):
        for vertex in independent_set:
            # Remove from self.vertices list
            self.vertices.pop(vertex.id)
            adjacent_vertices_list = list(vertex.adjacent_vertices)
            for adj_vertex in adjacent_vertices_list:
                adj_vertex.adjacent_vertices.discard(vertex)
                adj_vertex.degree = len(adj_vertex.adjacent_vertices)
            self.newly_removed_triangles_list = list(vertex.triangles)
            for triangle in self.newly_removed_triangles_list:  # Copy with list to avoid modification during iteration
                if triangle.id in self.active_triangles:
                    # remove from active triangles
                    self.active_triangles.pop(triangle.id)
                    # remove this triangle from all its vertices' triangles set
                    for tri_vertex in triangle.vertices:
                        tri_vertex.triangles.discard(triangle)
            self.retriangulate(vertex, adjacent_vertices_list)
            # build DAG search tree
            self.update_triangle_children()
            
        
        for v in (self.outer_triangle + list(self.vertices.values())):
            print(v.id, "adjacent_vertices", [adj.id for adj in v.adjacent_vertices], "faces:", [tri.id for tri in v.triangles])

    # make sure vertices form a simple polygon (sort the vertices by their angle using the atan2)
    def sort_vertices(self, vertex, vertices):
        sorted_vertices = sorted(vertices, key=lambda v: np.arctan2(v.y - vertex.y, v.x - vertex.x))
        return sorted_vertices


    def retriangulate(self, vertex, vertices):     
        # Sort vertices to form a simple polygon
        sorted_vertices = self.sort_vertices(vertex, vertices)
        
        # Convert sorted vertices into the format expected by the triangulation library
        vertices_array = np.array([[v.x, v.y] for v in sorted_vertices])
        segments = [[i, (i + 1) % len(sorted_vertices)] for i in range(len(sorted_vertices))]
        hole_poly = {
            'vertices': vertices_array,
            'segments': segments,
        }
        
        # Perform the triangulation
        triangulated = triangle.triangulate(hole_poly, 'p')
        print("**** re-triangulated**** ", triangulated)
        
        # Process triangulation results to create and add new triangles
        self.process_triangulation_results(sorted_vertices, triangulated, is_inside=False, is_leaf=False)


    def update_triangle_children(self):
        for added_triangle in self.newly_added_triangles_list:
            for removed_triangle in self.newly_removed_triangles_list:
                if triangles_overlap(added_triangle, removed_triangle):
                    added_triangle.add_child(removed_triangle)
            print(added_triangle.id, [c.id for c in added_triangle.children])

    def clear_vertices(self):
        for vertex in self.vertices.values():
            vertex.clear()
        for triangle in self.active_triangles.values():
            triangle.clear()
        TriangleNode._id_counter = 0
        self.vertices.clear()
        self.segments.clear()
        self.inside_triangles.clear()
        self.outside_triangles.clear()
        self.outer_triangle=None
        self.newly_removed_triangles_list.clear()
        self.newly_added_triangles_list.clear()
        self.indep_set.clear()
        self.active_triangles.clear()
        self.all_triangles.clear()
        self.refresh()