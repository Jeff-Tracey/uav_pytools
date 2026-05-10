#

import numpy as np
import matplotlib.pyplot as plt


# Functions to calculate perceived altitude

def alt_perceived(altitude, pressure, temperature):
    """
    Calculate the perceived altitude based on the given altitude, pressure, and temperature.
    
    Parameters:
    altitude (float): The altitude in meters.
    pressure (float): The pressure in hPa.
    temperature (float): The temperature in Celsius.
    
    Returns:
    float: The perceived altitude in meters.
    """
    # Constants
    P0 = 1013.25  # sea level standard atmospheric pressure in hPa
    T0 = 288.15   # sea level standard temperature in K
    L = 0.0065    # temperature lapse rate in K/m
    R = 287.05    # specific gas constant for dry air in J/(kg·K)
    
    # Convert temperature to Kelvin
    T = temperature + 273.15
    
    # Calculate the perceived altitude using the barometric formula
    perceived_altitude = (T0 / L) * (1 - (pressure / P0) ** ((R * L) / (R * T)))
    
    return perceived_altitude

def alt_perceived_2(altitude, pressure, temperature):
    """
    Calculate the perceived altitude based on the given altitude, pressure, and temperature.
    
    Parameters:
    altitude (float): The altitude in meters.
    pressure (float): The pressure in hPa.
    temperature (float): The temperature in Celsius.
    
    Returns:
    float: The perceived altitude in meters.
    """
    # Constants
    P0 = 1013.25  # sea level standard atmospheric pressure in hPa
    T0 = 288.15   # sea level standard temperature in K
    L = 0.0065    # temperature lapse rate in K/m
    R = 287.05    # specific gas constant for dry air in J/(kg·K)
    
    # Convert temperature to Kelvin
    T = temperature + 273.15
    
    # Calculate the perceived altitude using the barometric formula
    perceived_altitude = (T0 / L) * (1 - (pressure / P0) ** ((R * L) / (R * T)))
    
    return perceived_altitude

def alt_perceived_3(altitude, pressure, temperature):
    """
    Calculate the perceived altitude based on the given altitude, pressure, and temperature.
    
    Parameters:
    altitude (float): The altitude in meters.
    pressure (float): The pressure in hPa.
    temperature (float): The temperature in Celsius.
    
    Returns:
    float: The perceived altitude in meters.
    """
    # Constants
    P0 = 1013.25  # sea level standard atmospheric pressure in hPa
    T0 = 288.15   # sea level standard temperature in K
    L = 0.0065    # temperature lapse rate in K/m
    R = 287.05    # specific gas constant for dry air in J/(kg·K)
    
    # Convert temperature to Kelvin
    T = temperature + 273.15
    
    # Calculate the perceived altitude using the barometric formula
    perceived_altitude = (T0 / L) * (1 - (pressure / P0) ** ((R * L) / (R * T)))
    
    return perceived_altitude


