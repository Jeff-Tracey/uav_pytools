import argparse
import numpy as np

# from: https://enterprise-insights.dji.com/blog/ground-sample-distance
# GSDh = (sensor_height * altitude) / (focal_length x image_height)
# GSDw = (sensor_width * altitude) / (focal_length x image_width)
# The relevant GSD number will be whichever value is the lowest, to ensure you’re using the worst-case scenario.
# Mavic 3M specs see: https://sdk-forum.dji.net/hc/en-us/articles/12325496609689-What-is-the-custom-camera-parameters-for-Mavic-3-Enterprise-series-and-Mavic-3M

# -----------------------------------------------------------------------------
# functions
# -----------------------------------------------------------------------------

def GSDfromAGL(agl, specs):
    assert all([key in specs for key in ['sensor_width', 'sensor_height', 'focal_length', 'image_width', 'image_height']]), 'Missing specs'
    GSDh = (specs['sensor_height'] * agl) / (specs['focal_length'] * specs['image_height']) # units = m/px
    GSDw = (specs['sensor_width'] * agl) / (specs['focal_length'] * specs['image_width']) # units = m/px
    return GSDh, GSDw

def AGLfromGSD(gsd, specs):
    assert all([key in specs for key in ['sensor_width', 'sensor_height', 'focal_length', 'image_width', 'image_height']]), 'Missing specs'
    AGLh = (specs['focal_length'] * specs['image_height'] * gsd) / specs['sensor_height'] # units = m
    AGLw = (specs['focal_length'] * specs['image_width'] * gsd) / specs['sensor_width'] # units = m
    return AGLh, AGLw

delin = '\n# -----------------------------------------------------------------------------\n'

# -----------------------------------------------------------------------------
# parameters (put in YAML or JSON file)
# -----------------------------------------------------------------------------
SPECS = {
    'DJI_Mavic_3M': {
        'RGB': {
            'sensor_width': 17.4, # units = mm (sensor type 4/3 CMOS: Effective pixels 20MP)
            'sensor_height': 13, # units = mm
            'focal_length': 12.29, # units = mm (FOV - 84 degrees, equivalent 35mm format focal length 24mm)
            'image_width': 5280, # units = px
            'image_height': 3956 # units = px
        },
        'Multispectral': {
            'sensor_width': 5.2, # units = mm (sensor type 1/2.8 CMOS: Effective pixels 5MP)
            'sensor_height': 3.9, # units = mm
            'focal_length': 4.34, # units = mm (FOV - 73.91 degrees, equivalent 35mm format focal length 25mm)
            'image_width': 2592, # units = px
            'image_height': 1944 # units = px
        }
    }, 
    'DJI_Air_2S': { # Need to input specs
        'Wide': {
            'sensor_width': 6.17, # units = mm (sensor type 1/1.7 CMOS: Effective pixels 20MP)
            'sensor_height': 4.55, # units = mm
            'focal_length': 22.8, # units = mm (FOV - 88 degrees, equivalent 35mm format focal length 22mm)
            'image_width': 5472, # units = px
            'image_height': 3648 # units = px
        },
        'Tele': {
            'sensor_width': 6.17, # units = mm (sensor type 1/1.7 CMOS: Effective pixels 20MP)
            'sensor_height': 4.55, # units = mm
            'focal_length': 88.8, # units = mm (FOV - 31 degrees, equivalent 35mm format focal length 88mm)
            'image_width': 5472, # units = px
            'image_height': 3648 # units = px
        }
    }
}

# example: python3 calc_drone_gsd.py --image_type Multispectral --agl 100 --gsd 5 --debug
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate drone GSD')
    parser.add_argument('--drone', type=str, default='DJI_Mavic_3M', help='Drone type') # choice
    parser.add_argument('--image_type', type=str, default='RGB', help='Image type')
    parser.add_argument('--agl', type=float, default=100., help='Altitude above ground level (AGL) in meters')
    parser.add_argument('--gsd', type=float, default=5., help='Ground sample distance (GSD) in cm/px')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    # -----------------------------------------------------------------------------
    # print args
    # -----------------------------------------------------------------------------
    print(f'Drone type: {args.drone}')
    print(f'Image type: {args.image_type}')
    print(f'Altitude: {args.agl:.2f} m')
    print(f'GSD: {args.gsd:.2f} cm/px')

    assert args.drone in SPECS, 'Drone not found'
    assert args.image_type in SPECS[args.drone], 'Image type not found'
    specs = SPECS[args.drone][args.image_type]
    gsd = args.gsd / 100 # convert units to m/px

    # -----------------------------------------------------------------------------
    # given AGL, calculate GSD
    # -----------------------------------------------------------------------------
    print(f'{delin}Given AGL, calculate GSD for AGL = {args.agl:.2f} m{delin}')
    GSDh, GSDw = GSDfromAGL(args.agl, specs)
    gsd = min(GSDh, GSDw)
    print(f'GSDh = {GSDh:.6f} m/px, GSDw = {GSDw:.6f} m/px')
    print(f'GSD = {100 * gsd:.2f} cm/px')

    # -----------------------------------------------------------------------------
    # given GSD, calculate AGL
    # -----------------------------------------------------------------------------
    print(f'{delin}Given GSD, calculate AGL for GSD = {args.gsd:.2f} cm/px{delin}')
    agl_h, agl_w = AGLfromGSD(gsd, specs)
    agl = min(agl_h, agl_w)
    print(f'AGL = {agl_w:.2f} m (w), {agl_h:.2f} m (h)')
    print(f'AGL = {agl:.2f} m')
