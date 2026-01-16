from pathlib import Path


SEASON = 10
FIRST_MATCHES = [0, 100876, 338897, 519262, 674676, 909752, 1168208, 1499237, 1970845]
FINAL_MATCHES = [100875, 338896, 519261, 674675, 909751, 1168207, 1499236, 1970844, 3000000]
FOOTER_TEXT = "Support me! • ko-fi.com/naddy_mc • youtube.com/@naddy_mc"
FOOTER_ICON = "https://s3-eu-west-1.amazonaws.com/tpd/logos/6135e97910dcdc001dbff909/0x0.png"
SPLIT_CODES = [
    "story.enter_the_nether",
    "nether.find_bastion",
    "nether.find_fortress",
    "projectelo.timeline.blind_travel",
    "story.follow_ender_eye",
    "story.enter_the_end",
]
SPLIT_CODES_ALL = [
    "projectelo.timeline.reset",
    *SPLIT_CODES
]
SPLITS = ["ow", "nether", "bastion", "fortress", "blind", "stronghold", "end"]
SPLIT_MAP = {SPLIT_CODES_ALL[i]: SPLITS[i] for i in range(len(SPLIT_CODES_ALL))}
MAJOR_SPLITS = ["OVERWORLD", "NETHER", "POST_BLIND", "END"]
BASTIONS = ["BRIDGE", "HOUSING", "STABLES", "TREASURE"]
OVERWORLDS = ["BURIED_TREASURE", "DESERT_TEMPLE", "RUINED_PORTAL", "SHIPWRECK", "VILLAGE"]
OW_MAPPING = {
    "BURIED_TREASURE": "bt",
    "DESERT_TEMPLE": "dt",
    "RUINED_PORTAL": "rp",
    "SHIPWRECK": "ship",
    "VILLAGE": "village",
}
