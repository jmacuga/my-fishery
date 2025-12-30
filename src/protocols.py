from enum import Enum


class Protocols(Enum):
    IF_CAN_ENTER_REQUEST = "if_can_enter_request"
    IF_CAN_ENTER_RESPONSE = "if_can_enter_response"
    REGISTER_EXIT_REQUEST = "register_exit_request"
    REGISTER_EXIT_RESPONSE = "register_exit_response"
    IF_CAN_TAKE_FISH_REQUEST = "if_can_take_fish_request"
    IF_CAN_TAKE_FISH_RESPONSE = "if_can_take_fish_response"
    REGISTER_FISH_DATA_REQUEST = "register_fish_data_request"
    REGISTER_FISH_DATA_RESPONSE = "response_fish_data_response"
    SEND_NEEDS_STOCKING_ALARM = "send_needs_stocking_alarm"
    SEND_WATER_QUALITY_ALARM = "send_water_quality_alarm"
    WATER_QUALITY_ALARM = "water_quality_alarm"
