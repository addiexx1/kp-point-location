import numpy as np
import time
from shapely.geometry import Polygon, Point
import triangle
from panels.utils import point_inside_triangle, triangles_overlap
import pandas as pd
import matplotlib.pyplot as plt
class Vertex:
    def __init__(self, x, y, id):
        self.id = id  # vertice of outer triangle have ids 0, 1, 2, each user created vertex id starts from 3
        self.x = x
        self.y = y
        self.degree = 0
        self.adjacent_vertices = set()
        self.triangles = set()
        
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
    
    def clear(self):
        self.vertices = []
        self.children.clear()


class Kirkpatrick:
    def __init__(self, points):
        self.vertices = {}
        for i, p in enumerate(points):
            self.vertices[i+3] = Vertex(*p, i+3)
        self.triangles = []
        self.root = None  # Root of the DAG
        self.outer_triangle = None # outer bounding triangle vertices
        self.active_triangles = {}
        self.all_triangles = {}
        self.newly_removed_triangles_list = []
        self.newly_added_triangles_list = []
        self.indep_set = set()
 
        
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
        
    def triangulate_inside_polygon(self):
  
        num_vertices = len(self.vertices)
        vertices_list = list(self.vertices.values())
        vertices_array = np.array([[vertex.x, vertex.y] for vertex in vertices_list])
        hole_poly = {
            'vertices': vertices_array,
            'segments': [[i, (i + 1) % num_vertices] for i in range(num_vertices)], 
        }
        inner_triangulated = triangle.triangulate(hole_poly, 'p')
        
        self.process_triangulation_results(vertices_list, inner_triangulated, is_inside=True, is_leaf=True)
        
    def triangulate_outer_triangle(self):
        all_vertices  = self.outer_triangle + list(self.vertices.values())
        vertices_array = np.array([(vertex.x, vertex.y) for vertex in all_vertices])
        outer_segments = [[i, i + 1] for i in range(len(self.outer_triangle) - 1)] + [[len(self.outer_triangle) - 1, 0]]
        inner_segments_start_index = len(self.outer_triangle)
        inner_segments = [[i + inner_segments_start_index, i + 1 + inner_segments_start_index] for i in range(len(self.vertices.keys()) - 1)] + [[inner_segments_start_index + len(self.vertices.keys()) - 1, inner_segments_start_index]]
        
        hole_point = [self.calculate_centroid(list(self.active_triangles.values())[0].vertices)]
        hole_poly = {
            'vertices': vertices_array,
            'segments': outer_segments + inner_segments,
            'holes': hole_point
        }
        triangulated = triangle.triangulate(hole_poly, 'p')
        self.process_triangulation_results(all_vertices, triangulated, is_inside=False, is_leaf=True)

        
    def process_triangulation_results(self, vertices, triangulated, is_inside, is_leaf):
        new_triangles = {}

        # Iterate over the triangulation results to create TriangleNodes
        for tri_indices in triangulated['triangles']:
            tri_vertices = [vertices[i] for i in tri_indices]
                
            new_triangle = TriangleNode(tri_vertices, is_inside=is_inside, is_leaf=is_leaf)
            new_triangles[new_triangle.id] = new_triangle
            # Update vertex's adjacent set and triangle associations
            for vertex in tri_vertices:
                vertex.add_triangle(new_triangle)
                for adj_vertex in tri_vertices:
                    if vertex != adj_vertex:
                        vertex.add_adjacent_vertex(adj_vertex)

        # Update the active_triangles dictionary
        self.active_triangles.update(new_triangles)
        self.newly_added_triangles_list = list(new_triangles.values())
        
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
        # Process triangulation results to create and add new triangles
        self.process_triangulation_results(sorted_vertices, triangulated, is_inside=False, is_leaf=False)


    def update_triangle_children(self):
        for added_triangle in self.newly_added_triangles_list:
            for removed_triangle in self.newly_removed_triangles_list:
                if triangles_overlap(added_triangle, removed_triangle):
                    added_triangle.add_child(removed_triangle)

    def clear_vertices(self):
        for vertex in self.vertices.values():
            vertex.clear()
        for triangle in self.active_triangles.values():
            triangle.clear()
        TriangleNode._id_counter = 0
        self.vertices.clear()
        self.outer_triangle=None
        self.newly_removed_triangles_list.clear()
        self.newly_added_triangles_list.clear()
        self.indep_set.clear()
        self.active_triangles.clear() 

    def preprocessing(self):
        self.construct_outer_triangle()
        self.triangulate_inside_polygon()
        self.triangulate_outer_triangle()
        while len(self.active_triangles) > 1:
            self.indep_set = self.find_independent_set()
            self.remove_independent_set(self.indep_set)
        self.root = list(self.active_triangles.values())[0]
        
    def point_location(self, point):
        search_path = []
        traveler = self.root
        while not traveler.is_leaf:
            search_path.append(traveler)
            found = False
            for child in traveler.children:
                v1, v2, v3 = [(v.x, v.y) for v in child.vertices]
                if point_inside_triangle(point, v1, v2, v3):
                    traveler = child
                    found = True
                    break
            if not found:
                self.is_inside = False
                return False
                # Add the leaf to the search path
                
        search_path.append(traveler)  
        v1, v2, v3 = [(v.x, v.y) for v in traveler.vertices]
        if point_inside_triangle(point, v1, v2, v3):
            self.is_inside = traveler.is_inside
            return traveler.is_inside
        else:
            self.is_inside = False
            return False 

        
def generate_simple_polygon(num_sides):
    # Generate random points
    points = np.random.rand(num_sides, 2)
    
    # Calculate centroid
    centroid = np.mean(points, axis=0)
    
    # Sort points by angle to centroid
    angles = np.arctan2(points[:, 1] - centroid[1], points[:, 0] - centroid[0])
    sorted_points = points[np.argsort(angles)]
    
    # Return the sorted points
    return sorted_points

"""
    TEST Kirkpatrick POINT LOCATION PERFORMANCE
"""
                 
if __name__ == "__main__":
    # num_points = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000]
    # num_points = [1000, 2000, 3000]
    num_points = [n for n in range(500, 30001, 500)]
    preprocessing_times = []
    avg_query_times = []
    
    for n in num_points:
        points = generate_simple_polygon(n)
        polygon = Polygon(points) # testing the accuracy of the result using shapely  
        kp = Kirkpatrick(points)
        start_time = time.time()
        kp.preprocessing()
        preprocessing_times.append(time.time() - start_time)
        query_times = []
        for _ in range(500):
            point = np.random.rand(2)
            # shapely_point = Point(point)
            
            start_time = time.time()
            inside_kp  = kp.point_location(point)
            query_times.append(time.time() - start_time)
            
            inside_shapely = shapely_point.within(polygon)           
            # test point location result       
            if inside_kp  != inside_shapely:
                raise ValueError("Mismatch between Kirkpatrick and Shapely results for point:", point)
        avg_query_times.append(np.mean(query_times))
        
    # Table  
    results_df = pd.DataFrame({
        'Num Points': num_points,
        'Preprocessing Time': preprocessing_times,
        'Average Query Time': avg_query_times
    })

    print(results_df)
    # Save as a tab-separated values file (.txt)
    results_df.to_csv('results.txt', sep='\t', index=False)


    # Plotting
    # fig, ax1 = plt.subplots()

    # color = 'tab:red'
    # ax1.set_xlabel('Num Points')
    # ax1.set_ylabel('Preprocessing Time', color=color)
    # ax1.plot(results_df['Num Points'], results_df['Preprocessing Time'], color=color)
    # ax1.tick_params(axis='y', labelcolor=color)

    # ax2 = ax1.twinx()
    # color = 'tab:blue'
    # ax2.set_ylabel('Average Query Time', color=color)
    # ax2.plot(results_df['Num Points'], results_df['Average Query Time'], color=color)
    # ax2.tick_params(axis='y', labelcolor=color)

    # fig.tight_layout()
    # plt.title('Kirkpatrick Point Location Time Complexity')
    # plt.show()
    
    # Plot Preprocessing Time
    plt.figure(figsize=(10, 6))
    plt.plot(results_df['Num Points'], results_df['Preprocessing Time'], marker='o', linestyle='-', color='r')
    plt.title('Preprocessing Time Complexity Analysis')
    plt.xlabel('Number of Points')
    plt.ylabel('Preprocessing Time (seconds)')
    plt.grid(True, which="both", ls="--")
    plt.show()

    # Plot Average Query Time
    plt.figure(figsize=(10, 6))
    plt.plot(results_df['Num Points'], results_df['Average Query Time'], marker='o', linestyle='-', color='b')
    plt.title('Query Time Complexity Analysis ')
    plt.xlabel('Number of Points')
    plt.ylabel('Average Query Time (seconds)')
    plt.grid(True, which="both", ls="--")
    plt.show()
    
    # Plotting Preprocessing Time using a Log-Log Plot
    plt.figure(figsize=(10, 6))
    plt.loglog(results_df['Num Points'], results_df['Preprocessing Time'], marker='o', linestyle='-', color='r')
    plt.xlabel('Log Number of Points')
    plt.ylabel('Log Preprocessing Time (seconds)')
    plt.title('Preprocessing Time Complexity Analysis Log-Log Plot')
    plt.grid(True, which="both", ls="--")

    plt.show()
    
    # Plotting Preprocessing Time using a Semi-Log Plot (Logarithmic y-axis)
    plt.figure(figsize=(10, 6))
    plt.semilogy(results_df['Num Points'], results_df['Preprocessing Time'], marker='o', linestyle='-', color='r')
    plt.xlabel('Number of Points')
    plt.ylabel('Log Preprocessing Time (seconds)')
    plt.title('Preprocessing Time Complexity Analysis Semi-Log Plot (Log y-axis)')
    plt.grid(True, which="both", ls="--")

    plt.show()

    # Plotting Average Query Time using a Semi-Log Plot (Logarithmic y-axis)
    plt.figure(figsize=(10, 6))
    plt.semilogy(results_df['Num Points'], results_df['Average Query Time'], marker='o', linestyle='-', color='b')
    plt.xlabel('Number of Points')
    plt.ylabel('Log Average Query Time (seconds)')
    plt.title('Query Time Complexity Analysis Semi-Log Plot')
    plt.grid(True, which="both", ls="--")

    plt.show()
    
    # Plotting Average Query Time using a Log-Log Plot
    plt.figure(figsize=(10, 6))
    plt.loglog(results_df['Num Points'], results_df['Average Query Time'], marker='o', linestyle='-', color='b')
    plt.xlabel('Log Number of Points')
    plt.ylabel('Log Average Query Time (seconds)')
    plt.title('Query Time Complexity Analysis Log-Log Plot')
    plt.grid(True, which="both", ls="--")

    plt.show()