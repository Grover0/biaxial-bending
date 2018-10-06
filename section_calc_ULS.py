from math import pi, cos, sin, tan, atan, atan2, sqrt, ceil, floor
import numpy as np
import pandas as pd
import logging
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle, Wedge, Polygon
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import matplotlib.path as mpltPath
import geometry

'''
DESCRIPTION

    Sign convention
      Coordinate system           :   left handed
      Tension                     :   Positive
      Compression                 :   Negative

    - The term 'stress block' is used for the concrete area that, in the calculations, is assumed to be under compression.
      This area depends on the adopted stress-strain curve of the concrete, where the most used one is the Whitney Stress
      Block.
      In reality, everything on one side of the neutral axis is compression.

    -------------- FIND INTERSECTIONS BTW. NEUTRAL AXIS AND SECTION BOUNDARIES -----------
       Equation representing neutral axis:                     0 = tan(alpha) * x - y + na_y
       Equation representing inner edge of strees block        0 = tan(alpha) * x - y + na_y - delta_v
    where
      - 'delta_v' is the vertical distance between the neutral axis and the inner stress block edge
      - 'na_y' is the y-ccordinate of the intersection btw. the y-axis and the neutral axis.
'''

# TODO Neutral axis rotation should about plastic centroid, see 'Structural Analysis of Cross Sections', p. 190
# TODO Check for EQ between P, C and T after each run

# Create log file and set default logging statement
FORMAT = '%(name)-15s %(message)s'
filename = 'test.log'
logging.basicConfig(filename=filename, level=logging.DEBUG, filemode='w', format=FORMAT)

np.set_printoptions(precision=2)

def compute_plastic_centroid(x, y, xr, yr, As, fck, fyk):

    Ac = geometry.polygon_area(x, y)
    eta = 0.85
    F = sum([As[i]*fyk for i in As]) + eta*(Ac - sum(As))*fck

    # TODO Find correct and general arm for concrete force (polygon section)
    F_times_dx = sum([As[i]*fyk*xr[i] for i in range(len(xr))]) + eta*(Ac - sum(As))*fck*500/2
    F_times_dy = sum([As[i]*fyk*yr[i] for i in range(len(yr))]) + eta*(Ac - sum(As))*fck*375/2

    xpl = F_times_dx/F
    ypl = F_times_dy/F

    return xpl, ypl


def compute_dist_from_na_to_vertices(x, y, xr, yr, alpha_deg, na_y):

    alpha = alpha_deg * pi / 180    # [rad]

    # FIXME dv fails for pure compression
    # Find 'signed' distances from neutral axis to each vertex
    dv = []         # Initialize list for holding distances from each vertex to neutral axis

    # Define two known points on line representing neutral axis
    # NOTE Could be done more elegant if the function allowed tan(alpha) and na_y as input
    na_x0 = 0
    na_y0 = tan(alpha) * na_x0 + na_y
    na_x1 = 1
    na_y1 = tan(alpha) * na_x1 + na_y

    # Compute distances from neutral axis to each vertex (neg. value => vertex in compr. / pos. value => vertex in tension)
    # FIXME FIX DISTANCES FOR TENSION/COMPRESSION!!!
    for i in range(len(x)):
        dv.append( geometry.point_to_line_dist(x[i], y[i], na_x0, na_y0, na_x1, na_y1) )

    dr = []      # Distances btw. each rebar and neutral axis
    for i in range(len(xr)):
        dr.append( geometry.point_to_line_dist(xr[i], yr[i], na_x0, na_y0, na_x1, na_y1) )

    # Reverse sign of the 'signed' distances if slope of neutral axis becomes negative
    if alpha_deg > 90 and alpha_deg <= 270:
        dv = list(np.negative(dv))
        dr = list(np.negative(dr))

    # Change potential distances of '-0.0' to '0.0' to avoid getting the wrong cross section state later
    dv = [0.0 if x==-0.0 else x for x in dv]

    return dv, dr


def compute_stress_block_geomemtry(dv, dr, alpha_deg, na_y):
    '''
    Returns stress block geometry

    INPUT
        dv          -   List of distances from neutral axis to each section vertex
        dr          -   List of distances from neutral axis to each rebar
        alpha_deg   -
        na_y        -

    OUTPUT
        x_sb        -   List of x-coordinates of stress block vertices
        y_sb        -   List of y-coordinates of stress block vertices
        Asb         -   Area of stress block
        sb_cog      -   Cenntroid of stress block represented as tuple, i.e. in the format (x, y)
    '''

    # PURE TENSION CASE
    if all(d >= 0 for d in dv):         # NOTE Test is this is true! Does not account for  gap btw. sb and tension zone
        cross_section_state = 'PURE TENSION'

        # Distance from neutral axis to extreme tension bar (all distances will be positve)
        c = max([d for d in dr if d > 0])

        # Set vertices of stress block
        x_sb = None
        y_sb = None

        # Set stress block area
        Asb = 0

        sb_cog = None

    # PURE COMPRESSION CASE
    elif all(d <= 0 for d in dv):   # NOTE Test if this is true!
        cross_section_state = 'PURE COMPRESSION'

        # Distance from neutral axis to extreme compression fiber (all distances will be negative)
        c = min(dv)

        # Set vertices of stress block (entire section)
        x_sb = x
        y_sb = y

        Asb = geometry.polygon_area(x, y)
        sb_cog = geometry.polygon_centroid(x, y)

    # MIXED TENSION/COMPRESSION CASE
    else:
        cross_section_state = 'MIXED TENSION/COMPRESSION'

        # Distance from neutral axis to extreme compression fiber (pos. in tension / negative in compression)
        # FIXME This might not be correct in all cases (if compression zone is very small, tension will dominate)
        c = min(dv)

        # FIXME Fix naming below
        a = beta_1 * c                     # Distance from inner stress block edge to extreme compression fiber
        delta_p = c - a                    # Perpendicular distance between neutral axis and stress block
        alpha = alpha_deg*pi/180
        delta_v = delta_p / cos(alpha)     # Vert. dist. in y-coordinate from neutral axis to inner edge of stress block

        sb_y_intersect = na_y - delta_v     # Intersection between stress block inner edge and y-axis

        # Intersections between stress block and section
        sb_xint, sb_yint = geometry.line_polygon_collisions(alpha, sb_y_intersect, x, y)

        x_compr_vertices, y_compr_vertices = geometry.get_section_compression_vertices(x, y, na_y, alpha, delta_v)

        # Collect all stress block vertices
        x_sb = sb_xint + x_compr_vertices
        y_sb = sb_yint + y_compr_vertices

        # Order stress block vertices with respect to centroid for the entire section
        # NOTE Might fail for non-convex polygons, e.g. a T-beam
        x_sb, y_sb = geometry.order_polygon_vertices(x_sb, y_sb, x, y, counterclockwise=True)

        # Compute area of the stress block by shoelace algorithm
        Asb = geometry.polygon_area(x_sb, y_sb)

        # Compute location of centroid for stress block polygon
        sb_cog = geometry.polygon_centroid(x_sb, y_sb)

    return x_sb, y_sb, Asb, sb_cog, c


def compute_rebar_strain(dist_to_na, c, eps_cu):
    '''    Returns strain in each rebar as a list    '''
    return [ri / abs(c) * eps_cu for ri in dist_to_na]


def compute_rebar_stress(eps_r, Es, fyk):
    '''    Returns stress in each rebar as a list    '''
    # NOTE Could be expanded to handle both 'ULS' and 'SLS'
    sigma_r = []
    for i in range(len(eps_r)):
        si = eps_r[i] * Es                   # Linear elastic stress in i'th bar
        if abs(si) <= fyk:
            sigma_r.append(si)               # Use computed stress if it does not exceed yielding stress
        else:
            sigma_r.append(np.sign(si)*fyk)  # If computed stress exceeds yield, use yielding stress instead

    return sigma_r


def get_rebars_in_stress_block(xr, yr, x_sb, y_sb):
    '''    Returns a list with entry 'True' for rebars located inside the stress block, 'False' otherwise    '''
    # Arrange rebar coordinates
    rebar_coords = [[xr[i], yr[i]] for i in range(len(xr))]

    # Arrange stress block coordinates
    Asb = geometry.polygon_area(x_sb, y_sb)
    if Asb != 0:
        sb_poly = [[x_sb[i], y_sb[i]] for i in range(len(x_sb))]

        # Check if rebars are inside the stress block
        path = mpltPath.Path(sb_poly)
        rebars_inside = path.contains_points(rebar_coords)   # Returns 'True' if rebar is inside stress block
    else:
        # All rebars are in tension (all entries are 'False')
        rebars_inside = [False] * len(xr)

    return rebars_inside

    # logging.debug('bar {} is inside stress block'.format(i+1))  # TODO Create logging statement

def compute_rebar_forces(xr, yr, As, sigma_r, rebars_inside):
    ''' Return rebar forces as list'''
    Fr = []    # Forces in each rebar

    for i in range(len(xr)):
        if rebars_inside[i] == True:
        # Rebar is inside stress block, correct for disp. of concrete
            Fi = (sigma_r[i] + 0.85 * fcd) * As
        else:
            Fi = sigma_r[i] * As
        Fr.append(Fi)

    return Fr


def compute_concrete_force(fck, gamma_c, Asb):
    ''' Return compression force in the concrete. '''
    Fc = -0.85 * fck/gamma_c * Asb  
    return Fc

def compute_capacities(xr, yr, Fr, Fc, sb_cog, Asb):
    '''    Returns capacities P, Mx and My    '''

    # Moment contribution fram rebars about x- and y-axis (according to moment sign convention)
    # FIXME Lever arms should be taken wrt. the centroid of the transformed section, i.e. including reinforcement
    Mrx = [-Fr[i] * yr[i] for i in range(len(xr))]
    Mry = [-Fr[i] * xr[i] for i in range(len(xr))]

    if Asb == 0:
        Mcx = 0
        Mcy = 0
    else:
        # FIXME Moment lever arm should be distance between stress block centroid and centroid of transformed section __
        # FIXME __ Plastic centroid of transformed section happens to be at (0, 0) in the example in MacGregor's example
        Mcx = -Fc * sb_cog[1]    # Moment contribution from concrete in x-direction
        Mcy = -Fc * sb_cog[0]    # Moment contribution from concrete in y-direction

    # Total capacities
    P = sum(Fr) + Fc
    Mx = sum(Mrx) + Mcx
    My = sum(Mry) + Mcy

    return P, Mx, My


def compute_moment_vector_angle(Mx, My):
    '''    Returns the angle (in degrees) of the moment vector with respect to the x-axis    '''
    if Mx == 0:
        if My == 0:
            phi = None
        else:
            phi = 90
    else:
        phi = atan(My/Mx)*180/pi

    return phi


def compute_C_T_forces(Fc, Fr):
    '''    Returns Compression (C) and Tension (T) forces of the section    '''
    Fr_compr = [p for p in Fr if p <= 0]
    Fr_tension = [p for p in Fr if p > 0]
    C = sum(Fr_compr) + Fc
    T = sum(Fr_tension)

    return C, T


def compute_C_T_moments(C, T, Mcx, Mcy, Mry, Mrx, Fr):
    '''
    Returns total moments generated in the section by Compression (C) and Tension (T) resisting forces.

    The calculation assumes a left-handed sign convention.
    '''
    # TODO Change loop below to list comprehensions
    My_compr = []
    Mx_compr = []
    My_tension = []
    Mx_tension = []
    for i in range(len(Fr)):
        if Fr[i] < 0:
            My_compr.append(Mry[i])
            Mx_compr.append(Mrx[i])
        if Fr[i] > 0:
            My_tension.append(Mry[i])
            Mx_tension.append(Mrx[i])

    # Total moment for compression resisting forces (adapted for LH sign convention)
    if alpha_deg >= 90 and alpha_deg <= 270:
        My_C = sum(My_compr) + Mcy
        Mx_C = sum(Mx_compr) + Mcx
    else:
        My_C = -(sum(My_compr) + Mcy)
        Mx_C = -(sum(Mx_compr) + Mcx)

    # Total moment for tension resisting forces (adapted for LH sign convention)
    if alpha_deg >= 90 and alpha_deg <= 270:
        My_T = sum(My_tension)
        Mx_T = sum(Mx_tension)
    else:
        My_T = -sum(My_tension)
        Mx_T = -sum(Mx_tension)

    return Mx_C, My_C, Mx_T, My_T


def compute_C_T_forces_eccentricity(C, T, My_C, Mx_C, Mx_T, My_T):
    '''    Return eccentricity of Compression (C) and Tension (T) forces.    '''
    # Eccentricities of tension and compression forces
    if C == 0:
        ex_C = np.nan
        ey_C = np.nan
    else:
        ex_C = My_C/C
        ey_C = Mx_C/C

    if T == 0:
        ex_T = np.nan
        ey_T = np.nan
    else:
        ex_T = My_T/T
        ey_T = Mx_T/T

    return ex_C, ey_C, ex_T, ey_T


def compute_capacity_surface(x, y, xr, yr, fck, gamma_c, fyk, gamma_s, eps_cu,  rotation_step=5, vertical_step=10):
    ''' Returns coordinates for capacity surface of cross section (axial load and moments)'''
    # TODO Find a good way to define steps and loop over entire function
    # TODO Find a better way to represent increments for na_y, right now 0 is being computed twice __
    # TODO __ Stop varying na_y if pure tension or compression is found, i.e. if the moment capacities both become 0 __
    # TODO __ See GitHub Issue #2
    n = 8
    na_y_list = [-16*4/2*i/n for i in range(n)] + [16*4/2*i/n for i in range(n)]    # FIXME Improve!
    alpha_list = [alpha for alpha in range(0, 360, 5)]

    P_list = []
    Mx_list = []
    My_list = []
    na_y_computed = []
    alpha_computed = []

    # Loop over different positions of the neutral axis to create the capacity surface
    for na_y in na_y_list:
        for alpha_deg in alpha_list:
            na_y_computed.append(na_y)
            alpha_computed.append(alpha_deg)
            dv, dr = compute_dist_from_na_to_vertices(x, y, xr, yr, alpha_deg, na_y)
            x_sb, y_sb, Asb, sb_cog, c = compute_stress_block_geomemtry(dv, dr, alpha_deg, na_y)
            eps_r = compute_rebar_strain(dr, c, eps_cu)
            sigma_r = compute_rebar_stress(eps_r, Es, fyk)
            rebars_inside = get_rebars_in_stress_block(xr, yr, x_sb, y_sb)
            Fr = compute_rebar_forces(xr, yr, As, sigma_r, rebars_inside)
            Fc = compute_concrete_force(fck, gamma_c, Asb)
            P, Mx, My = compute_capacities(xr, yr, Fr, Fc, sb_cog, Asb)

            # Store iteration results
            P_list.append(P)
            Mx_list.append(Mx)
            My_list.append(My)

    return P_list, Mx_list, My_list, na_y_computed, alpha_computed





if __name__ == '__main__':

    # Define materials
    # NOTE eps_cu = 0.00035 in Eurocode for concrete strengths < C50
    eps_cu = 0.003      # Compressive crushing strain of concrete (strain when cross section capacity is reached)
    fck =  4    # [ksi]
    gamma_c = 1.0
    fcd = fck/gamma_c
    Es = 29000  # [ksi]
    fyk = 60     # [ksi]
    gamma_s = 1.0
    fyd = fyk/gamma_s

    # Define concrete geometry by polygon vertices
    x = [-8, 8, 8, -8]
    y = [8, 8, -8, -8]
    # x = [8, 8, -8]
    # y = [8, -8, -8]

    # Define rebar locations and sizes
    xr = [-5.6, 0,   5.6,  5.6,  5.6,  0,   -5.6, -5.6]
    yr = [ 5.6, 5.6, 5.6,  0,   -5.6, -5.6, -5.6,  0]
    # xr = [5.6,  5.6,  5.6,  1.0,   -3.5, 1.0]
    # yr = [3.5,  -1.0,   -5.6, -5.6, -5.6, -1.0]

    # Ø = ['insert rebar sizes']    # IMPLEMENT
    Ø = 1
    # As = pi * (Ø / 2)**2   # [in^2]    FIXME This is only the area of a single bar
    As = 0.79

    # NOTE lambda = 0.8 in Eurocode for concrete strengths < C50
    beta_1 = 0.85      # Factor for compression zone height of Whitney stress block

    # FIXME ZeroDivisionError in 'eps_r.append(dr[i] / c * eps_cu)' for (alpha, na_y)=(45, -16) or (0, -8) ___
    # FIXME ___ Happens just as the section goes from almost pure compression to pure compression. See plot!

    # FIXME Compression zone is not computed correctly if na is below section, FIX!!! Same problem as above comment I think!
    alpha_deg = 15               # [deg]
    na_y = -2       # [in] Distance from top of section to intersection btw. neutral axis and y-axis
    # NOTE na_y Should be infinite if alpha is 90 or 270

    P, Mx, My, na_y_computed, alpha_computed = compute_capacity_surface(x, y, xr, yr, fck, gamma_c, fyk, gamma_s, eps_cu)

    plot_capacity_surface(Mx, My, P)

    df = pd.DataFrame({'Mx': Mx, 'My': My, 'P': P, 'na_y': na_y_computed, 'alpha': alpha_computed})
    df.to_csv('df_results.csv', sep='\t')

    plot_ULS_section(x, y, xr, yr, -28, 0)

#####################################################
# LOGGING STATEMENTS
#####################################################
# logging.debug('Cross Section State    ' + cross_section_state)
# logging.debug('na_xint          ' + str(np.around(na_xint, decimals=2)))
# logging.debug('na_yint          ' + str(np.around(na_yint, decimals=2)))
# logging.debug('dv               ' + str(np.around(dv, decimals=2)))
# if cross_section_state == 'MIXED TENSION/COMPRESSION':
#     logging.debug('sb_xint          ' + str(np.around(sb_xint, decimals=2)))
#     logging.debug('sb_yint          ' + str(np.around(sb_yint, decimals=2)))
#     logging.debug('x-intersections btw. sb and section: {}'.format(sb_xint, '%.2f'))
#     logging.debug('y-intersections btw. sb and section: ' + str(sb_yint))
#     logging.debug('x_compr_vertices ' + str(x_compr_vertices))
#     logging.debug('y_compr_vertices ' + str(y_compr_vertices))
# if Asb != 0:
#     logging.debug('x_sb:        ' + str(np.around(x_sb, decimals=2)))
#     logging.debug('y_sb:        ' + str(np.around(y_sb, decimals=2)))
#     logging.debug('Asb:         ' + str(np.around(Asb, decimals=2)))
#     logging.debug('sb_cog       ' + str(np.around(sb_cog, decimals=2)))
# logging.debug('c                ' + str(c))
# logging.debug('Lever arm - dr   ' + str(np.around(dr, decimals=2)))
# logging.debug('Strain - Rebars  ' + str(eps_r))
# logging.debug('Stress - Rebars  ' + str(np.around(sigma_r, decimals=2)))
# logging.debug('Fr               ' + str(np.around(Fr, decimals=2)))
# logging.debug('sum(Fr)        ' + str(np.sum(Fr)))
# logging.debug('Fc               ' + str(np.around(Fc, decimals=2)))
# logging.debug('Mcx              ' + str(np.around(Mcx, decimals=2)))
# logging.debug('Mcy              ' + str(np.around(Mcy, decimals=2)))
# logging.debug('Mrx              ' + str(np.around(Mrx, decimals=2)))
# logging.debug('Mry              ' + str(np.around(Mry, decimals=2)))
# logging.debug('sum(Mrx)         ' + str(np.around(sum(Mrx), decimals=2)))
# logging.debug('sum(Mry)         ' + str(np.around(sum(Mry), decimals=2)))
# logging.debug('(P, Mx, My)      ' + str((np.around(P, decimals=2), np.around(Mx, decimals=2), np.around(My, decimals=2))))
# if phi is not None:
#     logging.debug('phi              ' + str(np.around(phi, decimals=2)))
# logging.debug('C:               {:.1f}'.format(C))
# logging.debug('T:               {:.1f}'.format(T))
# logging.debug('My_compr:        ' + str(My_compr))
# logging.debug('Mx_compr:        ' + str(Mx_compr))
# logging.debug('My_C:            {:.1f}'.format(My_C))
# logging.debug('Mx_C:            {:.1f}'.format(Mx_C))
# logging.debug('ey_C:            {:.1f}'.format(ey_C))
# logging.debug('ex_C:            {:.1f}'.format(ex_C))
# logging.debug('My_T:            {:.1f}'.format(My_T))
# logging.debug('Mx_T:            {:.1f}'.format(Mx_T))
# logging.debug('ey_T:            {:.1f}'.format(ey_T))
# logging.debug('ex_T:            {:.1f}'.format(ex_T))
