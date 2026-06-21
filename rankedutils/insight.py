from . import constants


def get_splits_naive(match: dict):
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

        if completion_time is not None and winner == uuid:
            split_times["end"] = completion_time - last_time

        player_split_times[uuid] = split_times

    return player_split_times


def get_event_times(desired_event: str, timeline: dict, uuid: str | None = None) -> list[int]:
    events = [
        event["time"]
        for event in timeline
        if event["type"] == desired_event
        and uuid is None or event["uuid"] == uuid
    ]
    return events


def get_match_completion(uuid: str, match: dict) -> int | None:
    if not match["forfeited"] and match["result"]["uuid"] == uuid:
        return match["result"]["time"]
    return None


def get_match_elo(uuid: str, match: dict) -> int | None:
    return next(change["eloRate"] for change in match["changes"] if change["uuid"] == uuid)


def get_throw_rate(uuid: str, detailed_matches: dict):
    throws = 0
    match_count = 0
    for match in detailed_matches:
        match_count += 1
        if any(
            event["type"]
            in ("projectelo.timeline.reset", "projectelo.timeline.death")
            for event in match["timelines"]
            if event["uuid"] == uuid
        ):
            throws += 1

    return round(throws / match_count * 100, 1)
