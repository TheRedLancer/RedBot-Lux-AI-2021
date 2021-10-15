from _typeshed import NoneType
import math, sys
from os import close
from typing import Optional
from lux import game_map
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, GameMap, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from lux.game_objects import *
import logging

logging.basicConfig(filename="agent.log", level=logging.INFO)

DIRECTIONS = Constants.DIRECTIONS
game_state = None

def get_closest_resource_tile(unit: Unit, player: Player, resource_tiles: list[Cell]) -> Optional[Cell]:
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(unit.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile

def get_closest_city_tile(unit: Unit, player: Player) -> Optional[CityTile]:
    closest_dist = math.inf
    closest_city_tile = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def get_closest_city(unit: Unit, player: Player) -> Optional[City]:
    closest_dist = math.inf
    closest_city = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city = city
    return closest_city

def get_closest_empty_tile(tile: Cell, player: Player, map: GameMap, tested_tiles: list[Cell]) -> Optional[Cell]:
    if (tile in tested_tiles):
        return None
    tested_tiles.append(tile)
    if tile.citytile == None and not tile.has_resource():
        # Base case: this tile is empty
        logging.info(f"{tile.pos} is not a city and not resources")
        return tile
    # implied else:
    curr_test_tile = None
    # Check all adjacent tiles for empty
    # An extended base case to minimize extra recursion
    for direction in {DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST}:
        try:
            curr_test_tile = map.get_cell_by_pos(tile.pos.translate(direction, 1))
        except IndexError:
            logging.info(f"Attempt to build out of bounds")
            pass
        # logging.info(f"{tile.pos} + {direction} + {curr_test_tile.pos}")
        if type(curr_test_tile) == Cell and curr_test_tile.citytile == None and not curr_test_tile.has_resource():
            return curr_test_tile

    closest_empty_tile = None
    closest_dist = math.inf
    # if no adjacent tiles are empty, run closest_empty_tile on each and compare results
    for direction in {DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST}:
        # find closest empty tile to the tile in each direction

        #TODO: actually validate input rather than trycatch
        try:
            curr_test_tile = get_closest_empty_tile(map.get_cell_by_pos(tile.pos.translate(direction, 1)), player, map, tested_tiles)
        except IndexError:
            logging.info(f"Attempt to build out of bounds")
            pass
        if type(curr_test_tile) == Cell:
            # get tile's distance to current tile
            dist = curr_test_tile.pos.distance_to(tile.pos)
            # compare tile's distance
            if dist < closest_dist:
                closest_empty_tile = curr_test_tile
                closest_dist = dist
    return closest_empty_tile
    # If none of them are empty
        # get the closest empty tile to each of them
        # compare the closest tiles of each of the adjacent ones
        # return the closest of those 4

def find_candidate_city(unit: Unit, map: GameMap) -> Cell:
    return map.get_cell(0,0)

def find_candidate_resource(unit: Unit, map: GameMap) -> Cell:
    return map.get_cell(1,1)

def build_city(unit: Unit, city_location: Cell, player: Player, resource_tiles: list[Cell], city_tiles: list[Cell]) -> str:
    global unit_missions
    global unit_destinations
    if unit.get_cargo_space_left == 0:
        # has resources to build city
        if unit.pos == city_location.pos:
            # build city and complete mission
            unit_missions.pop(unit.id)
            unit_destinations.pop(unit.id)
            return annotate.x(city_location.pos.x, city_location.pos.y)
        else:
            # go to city location
            return annotate.line(unit.pos.x, unit.pos.y, city_location.pos.x, city_location.pos.y)
    else:
        # go to closest resource to get fuel
        closest_resource = get_closest_resource_tile(unit, player, resource_tiles)
        if type(closest_resource) == Cell:
            return annotate.line(unit.pos.x, unit.pos.y, closest_resource.pos.x, closest_resource.pos.y)
        else:
            return annotate.sidetext("No closest Resource")

def get_resource(unit: Unit, res_location: Cell, player: Player, resource_tiles, city_tiles) -> str:
    global unit_missions
    global unit_destinations
    if unit.get_cargo_space_left == 0:
        # cargo full: go to nearest city to deposit
        nearest_city_tile = get_closest_city_tile(unit, player)
        if type(nearest_city_tile) == CityTile:
            if any([unit.pos.is_adjacent(tile.pos) for tile in city_tiles]):
                # arrived at city tile and finish mission
                unit_missions.pop(unit.id)
                unit_destinations.pop(unit.id)
                return annotate.line(unit.pos.x, unit.pos.y, nearest_city_tile.pos.x, nearest_city_tile.pos.y)
            else:
                # travel to nearest city
                return annotate.line(unit.pos.x, unit.pos.y, nearest_city_tile.pos.x, nearest_city_tile.pos.y)
        else:
            return annotate.sidetext("No closest City")
    else:
        # cargo empty: go to destination resource
        return annotate.line(unit.pos.x, unit.pos.y, res_location.pos.x, res_location.pos.y)

unit_missions: Dict[str, function] = {}

unit_destinations: Dict[str, Position] = {}


def agent(observation, configuration):
    global game_state
    global unit_missions
    global unit_destinations

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
                
    # clt = get_closest_empty_tile(game_state.map.get_cell(10, 10), player, game_state.map)
    # actions.append(annotate.circle(clt.pos.x, clt.pos.y))
    

    cities = player.cities.values()
    city_tiles = [c_tile for city in cities for c_tile in city.citytiles]

    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            #if city has fuel > 500 and worker has no space left
            closest_city = get_closest_city(unit, player)

            # if closest_city.fuel > 500 == 0:
            #     actions.append(annotate.x(1, 1))

            if unit.id in unit_missions:
                # unit continue mission
                logging.info(f'{unit.id} notice has {unit_missions[unit.id]} mission')
                actions.append(unit_missions[unit.id](unit, unit_destinations[unit.id], player, resource_tiles, city_tiles))
                unit_missions.pop(unit.id)
                unit_destinations.pop(unit.id)
            else:
                if type(closest_city) == City:
                    logging.info(f'{unit.id} notice have_city')
                    # we have a city
                    if closest_city.fuel > 500:
                        logging.info(f'{unit.id} notice city has {closest_city.fuel} fuel')
                        # go build city
                        unit_missions[unit.id] = build_city
                        unit_destinations[unit.id] = find_candidate_city(unit, game_state.map)
                        logging.info(f'{unit.id} going to build city at {unit_destinations[unit.id]}')
                    else:
                        # go get resources
                        # pick a resource to get
                        logging.info(f'{unit.id} notice city needs fuel')
                        unit_missions[unit.id] = get_resource
                        unit_destinations[unit.id] = find_candidate_resource(unit, game_state.map)
                else:
                    # we don't have a city
                    # go build city
                    unit_missions[unit.id] = build_city
                    unit_destinations[unit.id] = find_candidate_city(unit, game_state.map)
                    actions.append(unit_missions[unit.id](unit, unit_destinations[unit.id], player, resource_tiles, city_tiles))






            if type(closest_city) == City and unit.get_cargo_space_left() == 0 and closest_city.fuel > 500:
                #logging.info(f'Unit: {unit} is going to build a city')
                # logging.info(f"{unit.id} can build a new city")
                #find empty tile next to city
                closest_empty_tile_adj_city = get_closest_empty_tile(game_state.map.get_cell_by_pos(get_closest_city_tile(unit, player).pos), player, game_state.map, [])
                if type(closest_empty_tile_adj_city) == Cell:
                    actions.append(annotate.x(closest_empty_tile_adj_city.pos.x, closest_empty_tile_adj_city.pos.y))
                    # Found empty tile next to nearest city
                    # Prioritize expanding city over making new city
                    if unit.pos == closest_empty_tile_adj_city.pos:
                        actions.append(unit.build_city())
                    else:
                        move_dir = unit.pos.direction_to(closest_empty_tile_adj_city.pos)
                        actions.append(unit.move(move_dir))
                else:
                    # Not found city with empty adjacent tile
                    closest_empty_tile = get_closest_empty_tile(game_state.map.get_cell_by_pos(unit.pos), player, game_state.map, [])
                    move_dir = unit.pos.direction_to(closest_empty_tile.pos)
                    actions.append(unit.move(move_dir))

            elif type(closest_city) == NoneType:
                if not game_state.map.get_cell_by_pos(unit.pos).has_resource():
                    actions.append(unit.build_city())
                else:
                    closest_empty_tile = get_closest_empty_tile(game_state.map.get_cell_by_pos(unit.pos), player, game_state.map, [])
                    move_dir = unit.pos.direction_to(closest_empty_tile.pos)
                    actions.append(unit.move(move_dir))

            else:
                #logging.info(f'{unit.id} needs to find resource')
                closest_dist = math.inf
                if unit.get_cargo_space_left() > 0:
                    # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
                    closest_resource_tile = get_closest_resource_tile(unit, player, resource_tiles)
                    if type(closest_resource_tile) == Cell:
                        #logging.info(f'{unit.id} should go to {closest_resource_tile.pos}')
                        actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))
                else:
                    # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                    if len(player.cities) > 0:
                        closest_city_tile = get_closest_city_tile(unit, player)
                        if type(closest_city_tile) == CityTile:
                            move_dir = unit.pos.direction_to(closest_city_tile.pos)
                            actions.append(unit.move(move_dir))

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    for city_tile in city_tiles:
        if city_tile.can_act():
            if len(city_tiles) > len(player.units):
                actions.append(city_tile.build_worker())

    return actions
