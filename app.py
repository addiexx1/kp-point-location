# app.py
import tkinter as tk
from panels.kp_panel import KPPanel
from panels.dag_panel import DAGPanel
from panels.info_panel import InfoPanel

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kirkpatrick's Point Location Virtualizer")
        self.geometry("1250x800")
        self.phase = "DRAW"
        self.bind("<Return>", self.start_search_path)

        # Setup InfoPanel
        self.info_panel = InfoPanel(self, self, bg="lightgray", height=100)  
        self.info_panel.pack(side="top", fill="x", pady=10)

        # Frame for KPPanel and DAGPanel
        self.panel_frame = tk.Frame(self)
        self.panel_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # Setup KPPanel
        self.kp_panel = KPPanel(self.panel_frame, self, bg="#dfe4ed", width=650, height=700)
        self.kp_panel.pack(side="left", fill="y", expand=False)

        # Setup DAGPanel
        self.dag_panel = DAGPanel(self.panel_frame, self, self.kp_panel, bg="#dfedeb", width=600, height=700)
        self.dag_panel.pack(side="right", fill="y", expand=True)

    def update_phase(self, phase):
        self.phase = phase
        self.kp_panel.refresh()
        self.dag_panel.refresh()
        self.info_panel.update_phase_label(phase)

    def clear_drawing(self):
        self.kp_panel.delete("all")
        self.dag_panel.delete("all")
        self.kp_panel.clear_vertices()
        self.dag_panel.clear()
        self.update_phase("DRAW")

    def start_search_path(self, event=None):
        self.info_panel.label.config(text="`Enter` Pressed: Showing Search Path..... ")
        self.dag_panel.show_search_path()




if __name__ == "__main__":
    app = App()
    app.mainloop()

    def add_active_triangle(self, triangle):
        self.active_triangles.append(triangles)
    
    def remove_active_triangle(self, triangle):
        self.active_triangles