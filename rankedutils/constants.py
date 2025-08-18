SEASON = 8
FINAL_MATCHES = [100875, 338896, 519261, 674675, 909751, 1168207, 1499236, 1970844, 3000000]
FOOTER_TEXT = "By @nadoms • Send bugs & feedback! • youtube.com/@nqdoms"
FOOTER_ICON = "https://cdn.discordapp.com/avatars/298936021557706754/a_60fb14a1dbfb0d33f3b02cc33579dacf?size=256"
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
