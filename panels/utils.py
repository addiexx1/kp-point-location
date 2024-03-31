"""
Vertex Inside Triangle: Check if any vertex of one triangle is inside the other triangle. This can be determined using the barycentric coordinate method or by checking the sign of areas formed by the triangle and the point.

Edge Intersection: Check if any edges from the two triangles intersect. This involves checking if two line segments intersect, which can be done by comparing the orientations formed by endpoints of the segments.
"""

# def sign(p1, p2, p3):
#     return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

# def point_inside_triangle(pt, v1, v2, v3):
#     d1 = sign(pt, v1, v2)
#     d2 = sign(pt, v2, v3)
#     d3 = sign(pt, v3, v1)

#     has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
#     has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
#     return not (has_neg and has_pos)

# def point_strictly_inside_triangle(pt, v1, v2, v3):
#     d1 = sign(pt, v1, v2)
#     d2 = sign(pt, v2, v3)
#     d3 = sign(pt, v3, v1)

#     return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)

def point_inside_triangle(pt, v1, v2, v3):
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    b1 = sign(pt, v1, v2) < 0.0
    b2 = sign(pt, v2, v3) < 0.0
    b3 = sign(pt, v3, v1) < 0.0

    return ((b1 == b2) & (b2 == b3))

# def point_inside_triangle(triangle, point):
    
#     # Extract vertices of the triangle
#     A, B, C = triangle
    
#     # Calculate barycentric coordinates of the point
#     alpha = ((B[1] - C[1])*(point[0] - C[0]) + (C[0] - B[0])*(point[1] - C[1])) / \
#             ((B[1] - C[1])*(A[0] - C[0]) + (C[0] - B[0])*(A[1] - C[1]))
#     beta = ((C[1] - A[1])*(point[0] - C[0]) + (A[0] - C[0])*(point[1] - C[1])) / \
#            ((B[1] - C[1])*(A[0] - C[0]) + (C[0] - B[0])*(A[1] - C[1]))
#     gamma = 1.0 - alpha - beta
    
#     # Check if all barycentric coordinates are between 0 and 1
#     return 0 <= alpha <= 1 and 0 <= beta <= 1 and 0 <= gamma <= 1

# def triangle_contains_triangle(triangle1_vertices, triangle2_vertices):
#     # Iterate through each vertex in triangle2
#     for pt in triangle2_vertices:
#         # The * operator is used to unpack the triangle1 vertices into the function.
#         if not point_inside_triangle(pt, *triangle1_vertices):
#             return False
#     return True



# def strict_line_segment_intersect(p1, q1, p2, q2):
#     def orientation(p, q, r):
#         val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
#         if val == 0: return 0  # Collinear
#         return 1 if val > 0 else 2  # Clock or counterclockwise

#     def on_segment(p, q, r):
#         if orientation(p, q, r) != 0:
#             return False  # If they're not collinear they don't intersect
#         return (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
#                 q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]))

#     # Main orientation checks
#     o1 = orientation(p1, q1, p2)
#     o2 = orientation(p1, q1, q2)
#     o3 = orientation(p2, q2, p1)
#     o4 = orientation(p2, q2, q1)

#     # General case for strict intersection
#     if o1 != o2 and o3 != o4:
#         return True

#     return False


# def triangles_overlap(triangle1, triangle2):
#     # Unpack vertices
#     v1, v2, v3 = [(v.x, v.y) for v in triangle1.vertices]
#     u1, u2, u3 = [(u.x, u.y) for u in triangle2.vertices]
    
#     # Check for a vertex strictly inside the other triangle
#     for point in [v1, v2, v3]:
#         if point_inside_triangle(point, u1, u2, u3):
#             return True
#     for point in [u1, u2, u3]:
#         if point_inside_triangle(point, v1, v2, v3):
#             return True
    
#     # Check for strict edge intersection
#     edges1 = [(v1, v2), (v2, v3), (v3, v1)]
#     edges2 = [(u1, u2), (u2, u3), (u3, u1)]
#     for edge1 in edges1:
#         for edge2 in edges2:
#             if strict_line_segment_intersect(edge1[0], edge1[1], edge2[0], edge2[1]):
#                 return True
    
#     # If none of the strict checks pass, there's no genuine overlap
#     return False



from shapely.geometry import Polygon

def triangles_overlap(triangle1, triangle2):
    # Create Polygon objects for each triangle
    poly1 = Polygon([(v.x, v.y) for v in triangle1.vertices])
    poly2 = Polygon([(v.x, v.y) for v in triangle2.vertices])
    
    # Check if the two polygons overlap
    return poly1.overlaps(poly2) or poly1.contains(poly2) or poly2.contains(poly1)


# def triangles_overlap_shapely(triangle1, triangle2):
#     # Create Polygon objects for each triangle
#     poly1 = Polygon(triangle1)
#     poly2 = Polygon(triangle2)
    
#     # Check if the two polygons overlap
#     return poly1.intersects(poly2) or poly1.contains(poly2) or poly2.contains(poly1)

