# panels/info_panel.py
import tkinter as tk

phases = ["DRAW", "TRI", "FIND", "REMOVE", "SEARCH"]
class InfoPanel(tk.Frame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        self.clear_button = tk.Button(self, text="CLEAR X", font=('Arial', 11, 'bold'), command=self.clear_phase)
        self.clear_button.pack(side="left", padx=10, pady=10)

        self.continue_button = tk.Button(self, text="NEXT ->", font=('Arial', 11, 'bold'), command=self.next_phase)
        self.continue_button.pack(side="left", padx=10, pady=10)
        
        self.label = tk.Label(self, font=('Arial', 11, 'bold'), text="Start to draw: left click to add vertices, right click to remove")
        self.label.pack(side="right", padx=10, pady=10)

    def next_phase(self):
        current_index = phases.index(self.app.phase)
        if self.app.phase=="REMOVE" and len(self.app.kp_panel.active_triangles) > 1:
            next_phase = phases[(current_index - 1) % len(phases)]
        elif self.app.phase=="REMOVE" and len(self.app.kp_panel.active_triangles) == 1:
            next_phase = phases[(current_index + 1) % len(phases)]
            # set the root node
            self.app.dag_panel.root = list(self.app.kp_panel.active_triangles.values())[0]
        else:   
            next_phase = phases[(current_index + 1) % len(phases)]
            if next_phase == "DRAW":
                self.clear_phase()
        self.app.update_phase(next_phase)

    def clear_phase(self):
        self.app.clear_drawing()

    def update_phase_label(self, phase):
        phase_descriptions = {
            "DRAW": "Draw a Polygon:  Left Click to ADD vertices, Right Click to REMOVE vertices",
            "TRI": "Triangulation:  Outer Triangle and Triangulation, Click Next to Find Independent Set",
            "FIND": "Independent Set:  Click Next to Remove the Independent Set of Vertices!",
            "REMOVE": "Removed & Re-Triangulated:  Click Next to Find the Next Independent Set of Vertices!",
            "SEARCH": "Point Location:  Left Click to test if a Point is inside, Hit `Enter` to view Search Path"
        }
        self.label.config(text=phase_descriptions[phase])
