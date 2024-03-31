# panels/dag_panel.py
import tkinter as tk
from .utils import point_inside_triangle

class DAGPanel(tk.Canvas):
    def __init__(self, master, app, kp_panel, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.kp_panel = kp_panel
        self.node_radius = 14 
        self.layer_height = 90
        self.padding = 20 
        self.max_layers = 10
        self.node_horizontal_spacing = 32
        self.layer_vertical_spacing = 70
        self.layers = {} # start with layer 0 (leaf nodes)
        self.root = None
        self.search_path = []
        self.result_text_id = None
        self.highlight_node_id = []
        self.point = None
        self.is_inside = False

    def refresh(self):
        if self.app.phase == "REMOVE":
            print("REMOVE")
            # self.delete("all")
            self.draw_layer(list(self.kp_panel.active_triangles.values()))
            self.draw_edges()
        if self.app.phase == "SEARCH":
            print("SEARCH")            
        

    def draw_layer(self, triangles):
        layer_num = len(self.layers)
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        # Determine Y position of this layer, starting from the bottom
        y_position = height - (layer_num + 1) * self.layer_height + self.layer_height // 2
        num_nodes = len(triangles)
        total_spacing = (num_nodes - 1) * self.node_horizontal_spacing
        start_x_position = (width - total_spacing) / 2

        layer_positions = {}

        for index, triangle in enumerate(triangles):
            x_position = start_x_position + index * self.node_horizontal_spacing
            # Store the calculated position for each node in the current layer
            layer_positions[triangle.id] = (x_position, y_position)
            # Draw each node in the current layer
            self.draw_node(x_position, y_position, triangle.id)

        # Update self.layers with the current layer's positions
        self.layers[layer_num] = layer_positions

    def draw_node(self, x, y, node_id):
        node = self.kp_panel.all_triangles[node_id]
        fill_color = "white"
        if node.is_leaf:        
            fill_color = "#9af5b4" if node.is_inside else "#f5dd9a"
        self.create_oval(x - self.node_radius, y - self.node_radius,
                         x + self.node_radius, y + self.node_radius,
                         fill=fill_color, outline="black", width=1)
        self.create_text(x, y, text=str(node_id), font=("Arial", 12))     
        


    def draw_edges(self):
        if len(self.layers) < 2:
            return

        # Get the last and second-to-last layers
        current_layer_num = len(self.layers) - 1
        current_layer_positions = self.layers[current_layer_num]
        previous_layer_positions = self.layers[current_layer_num - 1]

        # Iterate through each node in the current layer
        for node_id, pos in current_layer_positions.items():
            node = self.app.kp_panel.all_triangles[node_id]
            
            # Check if the node exists in the previous layer and draw a self-edge
            if node_id in previous_layer_positions:
                start = pos
                end = previous_layer_positions[node_id]
                self.create_line(start[0], start[1]+10, end[0], end[1]-10, arrow=tk.LAST, fill="black", dash=(4, 2))
            # Draw edges to children in the previous layer
            for child in node.children:
                if child.id in previous_layer_positions:
                    start = pos
                    end = previous_layer_positions[child.id]
                    self.create_line(start[0], start[1]+10, end[0], end[1]-10, arrow=tk.LAST, fill="black")

    def point_location(self, point):
        self.search_path = []
        traveler = self.root
        while not traveler.is_leaf:
            self.search_path.append(traveler)
            found = False
            for child in traveler.children:
                v1, v2, v3 = [(v.x, v.y) for v in child.vertices]
                if point_inside_triangle(point, v1, v2, v3):
                    traveler = child
                    found = True
                    break
            if not found:
                print("SP", [s.id for s in self.search_path])
                self.is_inside = False
                return False  # Point is not inside any child; this shouldn't happen with a correct DAG
            
        # Add the leaf to the search path
        self.search_path.append(traveler)  
        print("SP", [s.id for s in self.search_path])
        v1, v2, v3 = [(v.x, v.y) for v in traveler.vertices]
        if point_inside_triangle(point, v1, v2, v3):
            self.is_inside = traveler.is_inside
            return traveler.is_inside
        else:
            self.is_inside = False
            return False 


    def draw_search_result(self, is_inside, point):
        width = self.winfo_reqwidth()
        if self.result_text_id is not None:
            self.delete(self.result_text_id)
        self.point = point
        result_text = "Point is Inside!" if is_inside else "Point is Outside!"
        color = "green" if is_inside else "red"
        self.result_text_id = self.create_text(width / 2, 20, text=result_text, fill=color, font=("Arial", 14, "bold"))   

    def show_search_path(self):
        if not self.search_path:
            print("Search path is empty.")
            return
        print("Search path ....")
        self.clear_highlights()
        num_layers = len(self.layers)
        root_id = num_layers - 1
        self.show_dag_path(root_id)
        
    def show_dag_path(self, i):
        if i < 0:
            return
        color = "green" if self.is_inside else "red"
        self.app.kp_panel.create_oval(self.point[0] - 3, self.point[1] - 3, self.point[0] + 3, self.point[1] + 3, fill=color, outline=color)
        # node id list
        search_path = [node.id for node in self.search_path]
        # matched node id set
        intersection = self.find_intersection_node(self.layers[i], search_path)
        if len(intersection) < 1:
            return
        node_id = intersection.pop()
        pos = self.layers[i][node_id]
        self.highlight_node(pos)
        self.app.kp_panel.delete("all")
        layer_triangles = [self.kp_panel.all_triangles[node] for node in self.layers[i].keys()]
        self.kp_panel.draw_triangulated_mesh(layer_triangles)
        # Draw the point
        self.app.kp_panel.create_oval(self.point[0] - 3, self.point[1] - 3, self.point[0] + 3, self.point[1] + 3, fill=color, outline=color)
        self.after(2000, lambda: self.show_dag_path(i-1))

    def highlight_node(self, pos):
        oval_id = self.create_oval(pos[0] - self.node_radius, pos[1] - self.node_radius,
                    pos[0] + self.node_radius, pos[1] + self.node_radius, outline="#4eaeed", width=3)
        self.highlight_node_id.append(oval_id)
     
    def find_intersection_node(self, layer, search_path):
        layer_set = set(layer.keys())
        search_path_set = set(search_path)
        intersection = layer_set.intersection(search_path_set)
        return intersection
            
    def clear_highlights(self):
        for oval in self.highlight_node_id:
            self.delete(oval)
        self.highlight_node_id = []
                
                
    def clear(self):
        self.search_path.clear()
        self.layers.clear()
        self.result_text_id = None
        self.root = None
        self.point = None
