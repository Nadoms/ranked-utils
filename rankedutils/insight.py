from . import constants


def get_splits_naive(match):
    timeline = list(reversed(match["timelines"]))
    completion_time = match["result"]["time"] if not match["forfeited"] else None
    winner = match["result"]["uuid"]
    uuids = [player["uuid"] for player in match["players"]]
    player_split_times = {}

    for uuid in uuids:
        split_times = {split: None for split in constants.SPLITS}
        last_time = 0
        last_split = "ow"
        seen_splits = []
        for event in timeline:
            if (
                event["uuid"] == uuid
                and event["type"] in constants.SPLIT_CODES
                and event["type"] not in seen_splits
            ):
                split_times[last_split] = event["time"] - last_time
                last_time = event["time"]
                last_split = constants.SPLIT_MAP[event["type"]]
                seen_splits.append(event["type"])

        if completion_time is not None and winner is not None:
            split_times["end"] = completion_time - last_time

        player_split_times[uuid] = split_times

    return player_split_times
