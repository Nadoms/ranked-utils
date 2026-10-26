from enum import StrEnum
import hashlib
import json
from os import getenv
from pathlib import Path
import sqlite3

from wonderwords import RandomWord

from . import constants

words = RandomWord()
ADJECTIVES = sorted(w.lower() for w in words.filter(include_parts_of_speech=["adjectives"]) if w.isalpha())
NOUNS = sorted(w.lower() for w in words.filter(include_parts_of_speech=["nouns"]) if w.isalpha())


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
        singles
        small_singles
        good_gaps
        o_level
        tower
        front_diagonal
        front_straight
        back_diagonal
        back_straight
        past_score
        past_count
        current_score
        current_count
        seasons
        word_id
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
    seed_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    insert_seed(cursor, seed_info)


def insert_seed(
    cursor: sqlite3.Cursor,
    seed_info: dict[str, any] | None,
):
    if not cursor or not seed_info or not seed_info.get("id"):
        return

    if cursor.execute("SELECT 1 FROM seeds WHERE id = ?", (seed_info["id"],)).fetchone():
        return

    variations = parse_variations(seed_info.get("variations"))
    cursor.execute(
        """
INSERT INTO seeds (
    id,
    overworld,
    bastion,
    structure_biome,
    bastion_biome,
    fortress_biome,
    structure_type,
    structure_contents,
    triples,
    singles,
    small_singles,
    good_gaps,
    o_level,
    tower,
    front_diagonal,
    front_straight,
    back_diagonal,
    back_straight,
    word_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            seed_info.get("id"),
            seed_info.get("overworld"),
            seed_info.get("nether"),
            variations.get("structure_biome") if seed_info.get("overworld") != "DESERT_TEMPLE" else "desert",
            variations.get("bastion_biome"),
            variations.get("fortress_biome"),
            variations.get("structure_type"),
            variations.get("structure_contents"),
            variations.get("triples"),
            variations.get("singles"),
            variations.get("small_singles"),
            variations.get("good_gaps"),
            variations.get("o_level"),
            variations.get("tower"),
            seed_info["endTowers"][0] if seed_info["endTowers"] else None,
            seed_info["endTowers"][1] if seed_info["endTowers"] else None,
            seed_info["endTowers"][2] if seed_info["endTowers"] else None,
            seed_info["endTowers"][3] if seed_info["endTowers"] else None,
            assign_word_id(cursor, seed_info["id"]),
        )
    )


def hash_seed_id(seed_id: str, salt: int = 0) -> str:
    digest = hashlib.sha256(f"{seed_id}:{salt}".encode()).digest()
    n = int.from_bytes(digest[:8], "big")
    adjective = ADJECTIVES[n % len(ADJECTIVES)]
    noun = NOUNS[(n // len(ADJECTIVES)) % len(NOUNS)]
    return f"{adjective}-{noun}"


def assign_word_id(cursor: sqlite3.Cursor, seed_id: str) -> str:
    salt = 0
    word_id = hash_seed_id(seed_id, salt)
    while word_id and cursor.execute("SELECT 1 FROM seeds WHERE word_id = ?", (word_id,)).fetchone():
        salt += 1
        word_id = hash_seed_id(seed_id, salt)
    return word_id


def name_seeds(cursor: sqlite3.Cursor) -> int:
    seed_info = query_db(
        cursor,
        table="seeds",
        where="word_id IS NULL",
        order="id"
    )
    for seed in seed_info:
        cursor.execute(
            "UPDATE seeds SET word_id = ? WHERE id = ?",
            (assign_word_id(cursor, seed[0]), seed[0]),
        )
    return len(seed_info)


def update_match_lite(
    cursor: sqlite3.Cursor,
    match: dict[str, any],
):
    if not cursor:
        return

    seed_info = match.get("seed")
    result = match.get("result") or {}
    values = {
        "type": match.get("type"),
        "category": match.get("category"),
        "gameMode": match.get("gameMode"),
        "result_uuid": result.get("uuid"),
        "time": result.get("time"),
        "forfeited": match.get("forfeited"),
        "decayed": match.get("decayed"),
        "season": match.get("season"),
        "date": match.get("date"),
        "seedType": match.get("seedType"),
        "bastionType": match.get("bastionType"),
        "tag": match.get("tag"),
        "seed_id": seed_info.get("id") if seed_info else None,
    }
    assignments = ", ".join(f"{col} = COALESCE({col}, :{col})" for col in values)

    cursor.execute(
        f"UPDATE matches SET {assignments} WHERE id = :id",
        {"id": match.get("id"), **values},
    )
    if cursor.rowcount > 0:
        insert_seed(cursor, seed_info)


def update_seed(
    cursor: sqlite3.Cursor,
    seed_id: str,
    values: dict[str, any],
    overwrite: bool = False,
):
    if not cursor or not seed_id or not values:
        return

    columns = [row[1] for row in cursor.execute("PRAGMA table_info(seeds)")]
    values = {col: val for col, val in values.items() if col in columns and col != "id"}
    assignments = ", ".join(
        f"{col} = :{col}" if overwrite
        else f"{col} = COALESCE({col}, :{col})"
        for col in values
    )

    cursor.execute(
        f"UPDATE seeds SET {assignments} WHERE id = :id",
        {"id": seed_id, **values},
    )


def delete_match(
    cursor: sqlite3.Cursor,
    match_id: int,
):
    if not cursor:
        return

    cursor.execute("DELETE FROM runs WHERE match_id = ?", (match_id,))
    cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))


class Variation(StrEnum):
    CHEST = "chest"
    TYPE = "type"
    BIOME = "biome"
    STRUCTURE = "structure"
    BASTION = "bastion"
    FORTRESS = "fortress"
    TRIPLE = "triple"
    SINGLE = "single"
    SMALL_SINGLE = "small_single"
    END_SPAWN = "end_spawn"
    END_TOWER = "end_tower"


def parse_variations(variations: list[str] | None):
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
        elif object == Variation.CHEST and attribute == Variation.STRUCTURE and value not in structure_contents:
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
    singles INTEGER,
    small_singles INTEGER,
    good_gaps INTEGER,
    o_level INTEGER,
    tower TEXT,
    front_diagonal INTEGER,
    front_straight INTEGER,
    back_diagonal INTEGER,
    back_straight INTEGER,
    past_score FLOAT,
    past_count INTEGER,
    current_score FLOAT,
    current_count INTEGER,
    seasons TEXT,
    word_id TEXT
)
    """)

    match_columns = [row[1] for row in cursor.execute("PRAGMA table_info(matches)")]
    seed_columns = [row[1] for row in cursor.execute("PRAGMA table_info(seeds)")]
    new_columns = {
        "past_score": "FLOAT",
        "past_count": "INTEGER",
        "current_score": "FLOAT",
        "current_count": "INTEGER",
        "seasons": "TEXT",
        "word_id": "TEXT",
    }
    for new_column in new_columns:
        if new_column not in seed_columns:
            cursor.execute(f"ALTER TABLE seeds ADD COLUMN {new_column} {new_columns[new_column]}")
    if "seed_id" not in match_columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN seed_id TEXT")
    for replay_header in ("replayExist", "replayExists"):
        if replay_header in match_columns:
            cursor.execute(f"ALTER TABLE matches DROP COLUMN {replay_header}")

    new_word_ids = name_seeds()
    if new_word_ids:
        print(f"Named {new_word_ids} new seeds")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_seed_id ON matches (seed_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_id ON runs (match_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_uuid ON runs (player_uuid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_season_type_decayed ON matches (season, type, decayed)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_word_id ON seeds (word_id)")


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
