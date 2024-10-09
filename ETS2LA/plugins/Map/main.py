# Imports to fix circular imports
import utils.prefab_helpers as ph
import utils.road_helpers as rh
import utils.math_helpers as mh
import utils.internal_map as im

# ETS2LA imports
from ETS2LA.plugins.runner import PluginRunner
from ETS2LA.utils.translator import Translate
import ETS2LA.backend.settings as settings
import ETS2LA.plugins.Map.classes as c
from utils.data_reader import ReadData
import route.planning as planning
import route.driving as driving

# General imports
import json
import data
import time
import math
import sys

api = None
steering = None
runner: PluginRunner = None

steering_smoothness = settings.Get("Map", "SteeringSmoothTime", 0.2)

def ToggleSteering(state:bool, *args, **kwargs):
    data.enabled = state

def Initialize():
    global api
    global steering
    
    data.runner = runner
    data.controller = runner.modules.SDKController.SCSController()
    data.map = ReadData()
    c.data = data # set the classes data variable
    api = runner.modules.TruckSimAPI
    
    steering = runner.modules.Steering
    steering.OFFSET = 0
    steering.SMOOTH_TIME = steering_smoothness
    steering.IGNORE_SMOOTH = False
    steering.SENSITIVITY = 1
    
def UpdateSteeringSettings(settings: dict):
    global steering_smoothness
    steering_smoothness = settings.get("SteeringSmoothTime", 0.2)
    steering.SMOOTH_TIME = steering_smoothness
    
settings.Listen("Map", UpdateSteeringSettings)
    
def plugin():
    api_data = api.run()
    data.UpdateData(api_data)
    runner.Profile("Main - API")
    
    if data.calculate_steering:
        planning.UpdateRoutePlan()
        runner.Profile("Main - Route Plan")
        steering_value = driving.GetSteering()
        steering.run(value=steering_value/180, sendToGame=data.enabled, drawLine=False)
        runner.Profile("Steering - Send to game")
    else:
        data.route_points = []
    
    if not data.map_initialized and data.internal_map:
        im.InitializeMapWindow()
        MAP_INITIALIZED = True
        
    if data.map_initialized and not data.internal_map:
        im.RemoveWindow()
        MAP_INITIALIZED = False
    
    if data.internal_map:
        im.DrawMap(runner)
        
    runner.Profile("Map")
    
    return_dict = {}
    if data.external_data_changed:
        external_data = json.dumps(data.external_data)
        print(f"External data changed, file size: {sys.getsizeof(external_data)/1000:.0f} KB")
        return_dict["map"] = json.loads(external_data)
        return_dict["map_update_time"] = data.external_data_time
        data.external_data_changed = False
    return_dict["target_speed"] = api_data["truckFloat"]["speedLimit"]
    return_dict["next_intersection_distance"] = 0
    
    return [point.tuple() for point in data.route_points], return_dict