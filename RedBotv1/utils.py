import math, sys
from lux import game_map
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from lux.game_map import DIRECTIONS

def find_empty_tile(unit, closest_city, map):
    tiles_checked = []
    closest_tile = None
    #for tile in city
    for city_tile in closest_city.citytiles:
        #for adjacent tiles
            adj_cells = []
            for direction in {DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST}:
                adj_cells.append(map.get_cell_by_pos(city_tile.pos.translate(direction, 1)))
            for cell in adj_cells:
                if not cell.has_resource():
                    if closest_tile != None and closest_tile.pos.distance_to(unit.pos) > cell.pos.distance_to(unit.pos):
                        closest_tile = cell
                #if empty
                    #calc distance, if min set
    return closest_tile