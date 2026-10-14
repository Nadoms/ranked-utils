from enum import StrEnum
import json
from os import getenv
from pathlib import Path
import sqlite3

from . import constants


def query_db(
    cursor: sqlite3.Cursor,
    table: str = "matches",
    items: str = "*",
    where: str | None = None,
    join: str | None = None,
    order: str | None = None,
    limit: int | None = None,
    debug: bool = False,
    **kwargs: any,
) -> sqlite3.Cursor:
    """
    matches keys:
        id
        type
        category
        gameMode
        result_uuid
        time
        forfeited
        decayed
        season
        date
        seedType
        bastionType
        tag
        replayExist
        seed_id
    players keys:
        uuid
        nickname
    runs keys:
        match_id
        player_uuid
        change
        eloRate
        timeline
    seeds keys:
        id
        overworld
        bastion
        structure_biome
        bastion_biome
        fortress_biome
        structure_type
        structure_contents
        triples
        doubles
        singles
        good_gaps
        o_level
        tower
        front_diagonal
        front_straight
        back_diagonal
        back_straight
    """
    conditions = [where] if where else []

    for key in kwargs:
        conditions.append(f"{key} = :{key}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    join_clause = f"JOIN {join}" if join else ""
    order_clause = f"ORDER BY {order}" if order else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
SELECT {items} FROM {table}
{join_clause}
{where_clause}
{order_clause}
{limit_clause}
    """

    if debug:
        cursor.execute(f"EXPLAIN QUERY PLAN {query}", kwargs)
        print(cursor.fetchone())

    return cursor.execute(query, kwargs)


def get_elo(
    cursor: sqlite3.Cursor,
    uuid: str,
    season: int = constants.SEASON,
) -> int | None:
    run = next(
        query_db(
            cursor,
            "runs",
            items="eloRate, change, match_id",
            order="match_id DESC",
            limit=1,
            player_uuid=uuid
        ),
        None
    )
    if not run or not run[0]:
        return None
    match = next(
        query_db(
            cursor,
            "matches",
            items="season",
            limit=1,
            id=run[2]
        )
    )
    if int(match[0]) != season:
        return None
    current_elo = run[0] + run[1]
    return current_elo


def get_sb(
    cursor: sqlite3.Cursor,
    uuid: str,
    season: int = constants.SEASON,
) -> int | None:
    match = next(
        query_db(
            cursor,
            "matches",
            items="time",
            order="time ASC",
            limit=1,
            type=2,
            result_uuid=uuid,
            forfeited=False,
            season=season,
        ),
        None
    )
    if match:
        return match[0]


def get_nick(
    cursor: sqlite3.Cursor,
    uuid: str,
) -> str | None:
    nick = next(
        query_db(
            cursor,
            "players",
            items="nickname",
            uuid=uuid,
        ),
        None
    )
    if nick:
        return nick[0]


def insert_match(
    cursor: sqlite3.Cursor,
    match: dict[str, any],
):
    if not cursor:
        return

    seed_info = match["seed"]

    cursor.execute(
        """
INSERT INTO matches (
    id,
    type,
    category,
    gameMode,
    result_uuid,
    time,
    forfeited,
    decayed,
    season,
    date,
    seedType,
    bastionType,
    tag,
    replayExist,
    seed_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            match.get("id"),
            match.get("type"),
            match.get("category"),
            match.get("gameMode"),
            match["result"].get("uuid"),
            match["result"].get("time"),
            match.get("forfeited"),
            match.get("decayed"),
            match.get("season"),
            match.get("date"),
            match.get("seedType"),
            match.get("bastionType"),
            match.get("tag"),
            match.get("replayExist"),
            seed_info.get("id") if seed_info else None,
        )
    )

    for player in match["players"]:
        cursor.execute(
            """
INSERT OR REPLACE INTO players (
    uuid,
    nickname
) VALUES (?, ?)
            """,
            (
                player.get("uuid"),
                player.get("nickname"),
            )
        )

    for change in match["changes"]:
        timeline = [
            {
                "time": event.get("time"),
                "type": event.get("type"),
            }
            for event in match["timelines"]
            if event.get("uuid") == change.get("uuid")
        ]
        timeline_json = json.dumps(timeline)
        cursor.execute(
            """
INSERT INTO runs (
    match_id,
    player_uuid,
    change,
    eloRate,
    timeline
) VALUES (?, ?, ?, ?, ?)
            """,
            (
                match.get("id"),
                change.get("uuid"),
                change.get("change"),
                change.get("eloRate"),
                timeline_json,
            )
        )

    if not seed_info or not seed_info["id"]:
        return

    variations = parse_variations(seed_info["variations"])
    cursor.execute(
        """
INSERT OR IGNORE INTO seeds (
    id,
    overworld,
    bastion,
    structure_biome,
    bastion_biome,
    fortress_biome,
    structure_type,
    structure_contents,
    triples,
    doubles,
    singles,
    good_gaps,
    o_level,
    tower,
    front_diagonal,
    front_straight,
    back_diagonal,
    back_straight
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            seed_info.get("id"),
            seed_info.get("overworld"),
            seed_info.get("bastion"),
            variations.get("structure_biome"),
            variations.get("bastion_biome"),
            variations.get("fortress_biome"),
            variations.get("structure_type"),
            variations.get("structure_contents"),
            variations.get("triples"),
            variations.get("doubles"),
            variations.get("singles"),
            variations.get("good_gaps"),
            variations.get("o_level"),
            variations.get("tower"),
            seed_info["endTowers"][0] if seed_info["endTowers"] else None,
            seed_info["endTowers"][1] if seed_info["endTowers"] else None,
            seed_info["endTowers"][2] if seed_info["endTowers"] else None,
            seed_info["endTowers"][3] if seed_info["endTowers"] else None,
        )
    )


class Variation(StrEnum):
    CHEST = "chest"
    TYPE = "type"
    BIOME = "biome"
    STRUCTURE = "structure"
    BASTION = "bastion"
    FORTRESS = "fortress"
    TRIPLE = "triple"
    DOUBLE = "double"
    SINGLE = "single"
    END_SPAWN = "end_spawn"
    END_TOWER = "end_tower"


def parse_variations(variations: list[str]):
    parsed_variations = {}
    if not variations:
        return parsed_variations

    structure_contents = []
    for variation in variations:
        object, attribute, value = variation.split(":")
        key = None

        if object == Variation.BIOME:
            if attribute in (Variation.STRUCTURE, Variation.BASTION, Variation.FORTRESS):
                key = f"{attribute}_biome"
        elif object == Variation.TYPE and attribute == Variation.STRUCTURE:
            key = "structure_type"
        elif object == Variation.CHEST and attribute == Variation.STRUCTURE:
            structure_contents.append(value)
        elif object == Variation.BASTION:
            key = f"{attribute}s"
        elif object == Variation.END_SPAWN:
            key = "o_level"
        elif object == Variation.END_TOWER:
            key = "tower"

        if key:
            parsed_variations[key] = value

    parsed_variations["structure_contents"] = json.dumps(structure_contents)
    return parsed_variations


def init_db(cursor: sqlite3.Cursor):
    cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    type INTEGER,
    category TEXT,
    gameMode TEXT,
    result_uuid TEXT,
    time INTEGER,
    forfeited BOOLEAN,
    decayed BOOLEAN,
    season INTEGER,
    date INTEGER,
    seedType TEXT,
    bastionType TEXT,
    tag TEXT,
    replayExist BOOLEAN,
    seed_id TEXT,
    FOREIGN KEY (seed_id) REFERENCES seeds(id)
)
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    uuid TEXT PRIMARY KEY,
    nickname TEXT
)
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS runs (
    match_id INTEGER,
    player_uuid TEXT,
    change INTEGER,
    eloRate INTEGER,
    timeline TEXT,
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (player_uuid) REFERENCES players(uuid)
)
    """)

    cursor.execute("""
CREATE TABLE IF NOT EXISTS seeds (
    id TEXT PRIMARY KEY,
    overworld TEXT,
    bastion TEXT,
    structure_biome TEXT,
    bastion_biome TEXT,
    fortress_biome TEXT,
    structure_type TEXT,
    structure_contents TEXT,
    triples INTEGER,
    doubles INTEGER,
    singles INTEGER,
    good_gaps INTEGER,
    o_level INTEGER,
    tower TEXT,
    front_diagonal INTEGER,
    front_straight INTEGER,
    back_diagonal INTEGER,
    back_straight INTEGER
)
    """)

    columns = [row[1] for row in cursor.execute("PRAGMA table_info(matches)")]
    if "seed_id" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN seed_id TEXT")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_seed_id ON matches (seed_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_id ON runs (match_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_uuid ON runs (player_uuid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_season_type_decayed ON matches (season, type, decayed)")


def start(db_path: Path | None = None) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    if not db_path:
        db_path = getenv("DB_PATH")
        if not db_path:
            raise ValueError("Database path must be provided")
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    return conn, cursor


def finish(conn: sqlite3.Connection):
    conn.commit()
    conn.close()


def main():
    conn, cursor = start()
    init_db(cursor)
    finish(conn)


if __name__ == "__main__":
    main()
