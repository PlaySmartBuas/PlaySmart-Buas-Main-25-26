"""
This module processes and analyzes match data from the Valorant API, providing detailed statistics such as
kills, deaths, assists, economy, agent information, and map callouts for each round of a match.
It interacts with the Riot Games API to fetch match and player data, and it uses pandas for data manipulation.
The module includes helper functions to normalise coordinates, fetch agent and weapon data,
and handle both live and backup data sources when necessary.

Key Functions:
- `load_bg_data`: Loads backup match data from a local JSON file in case of an API failure.
- `get_agent_data`: Fetches agent details from the Valorant API, using a cache to avoid redundant requests.
- `get_map_info`: Fetches map data from the Valorant API.
- `normalise_coordinates`: Converts raw map coordinates to normalised coordinates based on match data.
- `get_match_data`: Fetches match data from the Riot API, falling back to backup data if needed.
- `process_match`: Processes the match data and calculates relevant statistics for each round.
- `get_weapon_data`: Fetches weapon data based on the damage item and caches the results.
- `update_weapon_and_ability_names`: Updates weapon names in the match data DataFrame.
- `extract_round_player_stats`: Extracts player statistics for each round, including kills, deaths, assists, and ability casts.
- `extract_round_player_economy`: Extracts player economy data for each round, including credits, armor, and weapon used.

Dependencies:
- `httpx`: For making asynchronous HTTP requests to the Valorant API.
- `pandas`: For manipulating and analyzing the match and player data.
- `PIL`: For image processing, particularly agent icons.
- `matplotlib`: For displaying agent icons on visualizations.
- `dotenv`: For loading environment variables, specifically the Riot API key.

Environment Variables:
- `RIOT_API_KEY`: Required for accessing the Riot Games API.

Cache:
- `agent_cache`: Caches agent data to avoid redundant API requests.
- `weapon_cache`: Caches weapon data to avoid redundant API requests.

This module is designed to be used in an asynchronous environment, allowing multiple API requests to be processed concurrently.
"""

import os
import json
from io import BytesIO
import pandas as pd
import numpy as np
import httpx
import requests
from PIL import Image
from fastapi import HTTPException
from dotenv import load_dotenv
from matplotlib.offsetbox import OffsetImage


# Load environment variables
load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Agent cache to avoid redundant API calls
agent_cache = {}
weapon_cache = {}
armor_cache = {}
player_cache = {}


# Helper Functions
def load_bg_data():
    """
    Loads backup match data from the 'bg_data.json' file located in the '../data/game/' directory.
    This is used when the API call fails.

    Returns:
        dict: The loaded backup match data.

    Raises:
        HTTPException: If loading the backup data fails.
    """
    try:
        with open(
            "../data/game/bg_match_3.json",
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load backup data: {e}"
        ) from e


async def get_agent_data(character_id: str):
    """
    Fetches agent details (name and icon) from the Valorant API based on the provided character ID.
    This function caches the agent data to avoid redundant API calls.

    Args:
        character_id (str): The UUID of the agent.

    Returns:
        dict: A dictionary containing the agent's name and icon URL.

    Returns:
        None: If no agent data is found for the given character ID.
    """
    if character_id in agent_cache:
        return agent_cache[character_id]

    agents_url = "https://valorant-api.com/v1/agents"
    async with httpx.AsyncClient() as client:
        response = await client.get(agents_url)

    if response.status_code == 200:
        agents_data = response.json()
        for agent in agents_data["data"]:
            if agent["uuid"] == character_id:
                agent_cache[character_id] = {
                    "name": agent["displayName"],
                    "icon_url": agent["displayIcon"],
                }
                return agent_cache[character_id]

    return None


async def get_map_info():
    """
    Fetches all map data from the Valorant API.

    Returns:
        list: A list of map data.

    Raises:
        HTTPException: If the API call fails.
    """
    url = "https://valorant-api.com/v1/maps"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        raise HTTPException(
            status_code=response.status_code, detail="Failed to fetch map data"
        )


def load_map_image(match_info):
    """
    Loads the map image once using the URL in match_info.
    """
    url = match_info.iloc[0]["minimap"]
    return Image.open(requests.get(url, stream=True, timeout=5).raw)


def extract_normalization_params(match_info):
    """
    Extracts normalization parameters from match_info into a dictionary.
    """
    row = match_info.iloc[0]
    return {
        "x_multiplier": row["xMultiplier"],
        "y_multiplier": row["yMultiplier"],
        "x_scalar_to_add": row["xScalarToAdd"],
        "y_scalar_to_add": row["yScalarToAdd"],
    }


def normalise_coordinates(location, map_image, norm_params):
    """
    Converts raw map coordinates to normalized map coordinates.
    """
    if not location or "x" not in location or "y" not in location:
        return None

    raw_x = location["x"]
    raw_y = location["y"]

    normalized_x = (raw_y * norm_params["x_multiplier"]) + norm_params[
        "x_scalar_to_add"
    ]
    normalized_y = (raw_x * norm_params["y_multiplier"]) + norm_params[
        "y_scalar_to_add"
    ]

    # Scale by image dimensions
    normalized_x *= map_image.width
    normalized_y *= map_image.height

    return {"x": float(normalized_x), "y": float(normalized_y)}


def normalize_coordinates_for_df(
    row, map_image, norm_params, coordinate_columns
):
    """
    Normalizes coordinates in the specified columns of a DataFrame row.
    """
    for column in coordinate_columns:
        value = row.get(column)

        if isinstance(value, dict):
            row[column] = normalise_coordinates(value, map_image, norm_params)

        elif isinstance(value, list):
            for idx, entry in enumerate(value):
                if isinstance(entry, dict) and "location" in entry:
                    normalized_location = normalise_coordinates(
                        entry["location"], map_image, norm_params
                    )
                    if normalized_location:
                        row[column][idx]["location"] = normalized_location

    return row


# Main Functions
async def get_match_data(match_id: str, shard: str):
    """
    Fetches match data from Riot's official API asynchronously. If the API request fails,
    it loads backup data from a local source.

    Args:
        match_id (str): The ID of the match.
        shard (str): The shard where the match is hosted (e.g., 'na', 'eu').

    Returns:
        dict: The match data as a dictionary.

    Raises:
        HTTPException: If both the official API and the backup data load fail.
    """
    riot_url = (
        f"https://{shard}.api.riotgames.com/val/match/v1/matches/{match_id}"
    )

    async with httpx.AsyncClient() as client:
        try:
            # Try fetching from the official Riot API first
            response = await client.get(
                riot_url, headers={"X-Riot-Token": RIOT_API_KEY}, timeout=5
            )
            response.raise_for_status()  # Will raise an exception for non-2xx status codes
            return response.json()
        except httpx.HTTPStatusError:
            # Handle 401 or other errors and fall back to the dummy data
            return load_bg_data()
        except httpx.RequestError:
            # Handle other connection errors
            return load_bg_data()


async def process_match(match_id: str, shard: str) -> pd.DataFrame:
    """
    Fetches match data and processes it into structured game statistics, including details of kills,
    assists, and player agents.

    Args:
        match_id (str): The ID of the match.
        shard (str): The shard where the match is hosted.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the processed match statistics.
    """
    match_data = await get_match_data(match_id, shard)
    map_info_list = await get_map_info()
    defuse_df = await get_defuse(match_data)
    map_id = match_data.get("matchInfo", {}).get("mapId", "")
    map_info = next((m for m in map_info_list if m["mapUrl"] == map_id), None)

    if not map_info:
        raise HTTPException(status_code=500, detail="Map info not found")

    game_stats = []

    for round_result in match_data.get("roundResults", []):
        for player_stat in round_result.get("playerStats", []):
            for kill_event in player_stat.get("kills", []):
                killer_id = kill_event.get("killer")
                victim_id = kill_event.get("victim")

                game_time = kill_event.get("gameTime")
                round_time = kill_event.get("roundTime")

                killer_agent = await get_agent_data(
                    next(
                        (
                            p["characterId"]
                            for p in match_data["players"]
                            if p["subject"] == killer_id
                        ),
                        None,
                    )
                )
                victim_agent = await get_agent_data(
                    next(
                        (
                            p["characterId"]
                            for p in match_data["players"]
                            if p["subject"] == victim_id
                        ),
                        None,
                    )
                )

                victim_location = kill_event.get("victimLocation", {})

                player_locations = [
                    {"subject": loc["subject"], "location": loc["location"]}
                    for loc in kill_event.get("playerLocations", [])
                ]

                game_stats.append(
                    {
                        "round": round_result.get("roundNum"),
                        "killer": killer_id,
                        "victim": victim_id,
                        "gameTime": game_time,
                        "roundTime": round_time,
                        "victimLocation": victim_location,
                        "playerLocations": player_locations,
                        "assistants": kill_event.get("assistants", []),
                        "finishingDamage": kill_event.get("finishingDamage"),
                        "isSecondaryFireMode": kill_event.get(
                            "isSecondaryFireMode", False
                        ),
                        "killerAgent": (
                            killer_agent["name"] if killer_agent else "Unknown"
                        ),
                        "victimAgent": (
                            victim_agent["name"] if victim_agent else "Unknown"
                        ),
                        "killerAgentIcon": (
                            killer_agent["icon_url"] if killer_agent else None
                        ),
                        "victimAgentIcon": (
                            victim_agent["icon_url"] if victim_agent else None
                        ),
                    }
                )

        match_info, map_callouts = await get_match_info(match_data)
        economy_df = await extract_round_player_economy(match_data)

    return (
        match_data,
        pd.DataFrame(game_stats),
        match_info,
        map_callouts,
        economy_df,
        defuse_df,
    )


async def get_defuse(match_data):
    """
    Fetches match data and extracts defuse-related information for each round.

    Args:
        match_id (str): The ID of the match.
        shard (str): The shard where the match is hosted.

    Returns:
        pd.DataFrame: A pandas DataFrame containing defuse statistics for each round.
    """

    defuse_stats = []

    for round_result in match_data.get("roundResults", []):
        defuse_round_time = round_result.get("defuseRoundTime", None)
        defuse_location = round_result.get("defuseLocation", {}) or {}
        bomb_planter = round_result.get("bombPlanter", "N/A")

        defuse_player_locations = [
            {
                "subject": loc.get("subject", "Unknown"),
                "viewRadians": loc.get("viewRadians", 0.0),
                "location": loc.get("location", {}),
            }
            for loc in round_result.get("defusePlayerLocations", []) or []
        ]

        defuse_stats.append(
            {
                "round": round_result.get("roundNum", None),
                "defuseRoundTime": defuse_round_time,
                "defuseLocation": defuse_location,
                "defusePlayerLocations": defuse_player_locations,
                "bombPlanter": bomb_planter,
            }
        )

    return pd.DataFrame(defuse_stats)


async def get_match_info(match_data: dict):
    """
    Fetches additional match information (e.g., map name, game start time, game length)
    and processes it into structured match data.

    Args:
        match_data (dict): The match data.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: The processed match information.
            - pd.DataFrame: The map callouts as a DataFrame.
    """
    match_info_list = []
    map_info_list = await get_map_info()

    map_id = match_data.get("matchInfo", {}).get("mapId", "")
    map_info = next((m for m in map_info_list if m["mapUrl"] == map_id), None)

    # Match information
    match_info_list.append(
        {
            "mapName": map_info.get("displayName", "Unknown"),
            "gameStartMillis": match_data.get("matchInfo", {}).get(
                "gameStartMillis", ""
            ),
            "gameLengthMillis": match_data.get("matchInfo", {}).get(
                "gameLengthMillis", ""
            ),
            "isCompleted": match_data.get("matchInfo", {}).get(
                "isCompleted", ""
            ),
            "xMultiplier": map_info.get("xMultiplier", "Unknown"),
            "yMultiplier": map_info.get("yMultiplier", "Unknown"),
            "xScalarToAdd": map_info.get("xScalarToAdd", "Unknown"),
            "yScalarToAdd": map_info.get("yScalarToAdd", "Unknown"),
            "minimap": map_info.get("displayIcon", "Unknown"),
        }
    )

    match_info_df = pd.DataFrame(match_info_list)

    # Extract callouts
    if "callouts" in map_info and isinstance(map_info["callouts"], list):
        map_callouts_df = pd.json_normalize(map_info["callouts"])
    else:
        map_callouts_df = pd.DataFrame()

    # Return both DataFrames separately
    return match_info_df, map_callouts_df


async def get_player_data(match_id, shard):
    """
    Fetches and processes player data from the match,
    including kills, deaths, assists, and abilities.

    Args:
        match_id (str): The ID of the match.
        shard (str): The shard where the match is hosted.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the player's statistics.
    """
    player_stats_df = pd.json_normalize(
        data=await get_match_data(match_id, shard),
        record_path=["players"],  # This flattens the players field
        meta=[
            "matchInfo.matchId",
            "matchInfo.mapId",
            "matchInfo.gameLengthMillis",
            "matchInfo.gameStartMillis",
            "matchInfo.isCompleted",
            "matchInfo.queueId",
            "matchInfo.gameMode",
        ],
        errors="ignore",
    )

    columns_to_keep = [
        "subject",
        "teamId",
        "characterId",
        "stats.kills",
        "stats.deaths",
        "stats.assists",
        "stats.abilityCasts.grenadeCasts",
        "stats.abilityCasts.ability1Casts",
        "stats.abilityCasts.ability2Casts",
        "stats.abilityCasts.ultimateCasts",
        "participationPeriods",
        "stats.score",
    ]
    return player_stats_df[columns_to_keep]


def extract_killer_location(row):
    """
    Extracts the killer's location from the playerLocations list by
    matching the subject with the killer ID.

    Args:
        row (pd.Series): A row from the DataFrame.

    Returns:
        dict: The location dictionary of the killer if found, otherwise an empty dictionary.
    """
    for player in row["playerLocations"]:
        if player["subject"] == row["killer"]:
            return player["location"]
    return {}  # Return empty dict if no match found


async def get_armor_data(armor_uuid: str):
    """
    Fetches armor details (display name) from the Valorant API using UUID.
    Caches the armor data to avoid redundant API calls.

    Args:
        armor_uuid (str): The UUID of the armor item.

    Returns:
        dict: A dictionary containing the armor's display name.
        None: If no armor data is found.
    """
    if armor_uuid in armor_cache:
        return armor_cache[armor_uuid]

    armor_url = "https://valorant-api.com/v1/gear"

    async with httpx.AsyncClient() as client:
        response = await client.get(armor_url)

    if response.status_code == 200:
        armor_data = response.json()
        for armor in armor_data.get("data", []):
            armor_cache[armor["uuid"]] = {
                "displayName": armor.get("displayName")
            }

        return armor_cache.get(armor_uuid)

    return None


async def get_weapon_data(damage_item: str):
    """
    Fetches weapon details (display name and display icon) from the Valorant API.
    Caches the weapon data to avoid redundant API calls.

    Args:
        damage_item (str): The weapon's internal UUID.

    Returns:
        dict: A dictionary containing the weapon's display name and icon.
        None: If no weapon data is found.
    """
    if damage_item in weapon_cache:
        return weapon_cache[damage_item]  # Return cached data

    weapon_url = "https://valorant-api.com/v1/weapons"

    async with httpx.AsyncClient() as client:
        response = await client.get(weapon_url)

    if response.status_code == 200:
        weapons_data = response.json()
        for weapon in weapons_data["data"]:
            if weapon["uuid"] == damage_item:
                weapon_cache[damage_item] = {  # Store both values correctly
                    "displayName": weapon["displayName"],
                    "displayIcon": weapon["displayIcon"],
                }
                return weapon_cache[damage_item]  # Return stored data

    return None


async def get_player_name(df, match_data, column):
    """
    Updates the given DataFrame column by replacing player UUIDs with their corresponding game names.
    Caches player data to avoid redundant lookups.

    Args:
        df (pd.DataFrame): The DataFrame containing the player UUIDs.
        match_data (dict): The match data containing player information.
        column (str): The column name in the DataFrame to update.

    Returns:
        pd.DataFrame: The updated DataFrame with player names.
    """

    # If cache is empty, populate it from match_data
    if (
        not player_cache
        and "players" in match_data
        and isinstance(match_data["players"], list)
    ):
        for player in match_data["players"]:
            player_id = player.get("subject")
            game_name = player.get("gameName", "Unknown")
            tag_line = player.get("tagLine", "Unknown")
            if player_id:
                player_cache[player_id] = f"{game_name}#{tag_line}"

        # Debugging: Print player cache to verify correct mappings

    # Replace UUIDs in the specified column using the cache
    df[column] = df[column].map(player_cache)

    return df


async def update_economy_display_names(economy_df):
    """
    Updates the economy DataFrame by replacing weapon and armor UUIDs with their respective display names.
    """
    for index, row in economy_df.iterrows():
        weapon_uuid = row.get("weapon", "").lower()
        armor_uuid = row.get("armor", "").lower()

        weapon_info = (
            await get_weapon_data(weapon_uuid) if weapon_uuid else None
        )
        armor_info = await get_armor_data(armor_uuid) if armor_uuid else None

        economy_df.at[index, "weapon"] = (
            weapon_info.get("displayName")
            if weapon_info
            else row.get("weapon")
        )
        economy_df.at[index, "armor"] = (
            armor_info.get("displayName") if armor_info else row.get("armor")
        )

    return economy_df


async def get_agent_ability_data(agent_name: str, ability_name: str):
    """
    Fetches agent ability details (display name and display icon) from the Valorant API.
    Caches the ability data to avoid redundant API calls.

    Args:
        agent_name (str): The name of the agent (to match with displayName).
        ability_name (str): The name of the ability (to match with slot).

    Returns:
        dict: A dictionary containing the ability's display name and icon.
        None: If no ability data is found.
    """
    if agent_name in agent_cache:
        # Check if the ability exists in cache
        for ability in agent_cache[agent_name]:
            if ability["slot"].lower() == ability_name.lower():
                return {
                    "displayName": ability["displayName"],
                    "displayIcon": ability["displayIcon"],
                }
        return None  # Ability not found in cache

    agent_url = "https://valorant-api.com/v1/agents"

    async with httpx.AsyncClient() as client:
        response = await client.get(agent_url)

    if response.status_code == 200:
        agent_data = response.json()
        # Find the agent that matches the name
        for agent in agent_data["data"]:
            if agent["displayName"].lower() == agent_name.lower():
                # Cache the abilities of this agent
                agent_cache[agent_name] = agent["abilities"]

                # Search for the correct ability
                for ability in agent["abilities"]:
                    if ability["slot"].lower() == ability_name.lower():
                        return {
                            "displayName": ability["displayName"],
                            "displayIcon": ability["displayIcon"],
                        }

    return None


async def get_abilities(player_stats_df):
    """
    Fetches the ability details (displayName and displayIcon) for each player
    based on their characterId from the Valorant API and adds them to the player_stats_df.

    Args:
        player_stats_df (pd.DataFrame): The DataFrame containing player stats with 'characterId'.

    Returns:
        pd.DataFrame: The updated player_stats_df with added abilities information.
    """
    abilities_data = []

    # Fetch the agent abilities for each unique characterId in the DataFrame
    async with httpx.AsyncClient() as client:
        # Updated API URL with the correct endpoint and filter parameter
        url = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
        response = await client.get(url)

        # Check if the response status is OK
        if response.status_code == 200:
            try:
                # Attempt to parse the response as JSON
                data = response.json().get("data", [])
                # For each characterId, find the agent and get its abilities
                for _, row in player_stats_df.iterrows():
                    character_id = row["characterId"]
                    # Find agent by characterId
                    agent = next(
                        (
                            agent
                            for agent in data
                            if agent["uuid"] == character_id
                        ),
                        None,
                    )
                    if agent:
                        # Match abilities with corresponding stats columns
                        abilities_dict = {}
                        for ability in agent.get("abilities", []):
                            slot = ability.get("slot")
                            display_name = ability.get("displayName", "N/A")
                            display_icon = ability.get("displayIcon", "N/A")
                            abilities_dict[slot] = {
                                "display_name": display_name,
                                "display_icon": display_icon,
                            }

                        # Now for each row, match the ability stats to the respective abilities
                        row_abilities = {
                            "grenadeCast": abilities_dict.get(
                                "Grenade", {}
                            ).get("display_name", "N/A"),
                            "grenadeCastIcon": abilities_dict.get(
                                "Grenade", {}
                            ).get("display_icon", "N/A"),
                            "Ability1Cast": abilities_dict.get(
                                "Ability1", {}
                            ).get("display_name", "N/A"),
                            "Ability1CastIcon": abilities_dict.get(
                                "Ability1", {}
                            ).get("display_icon", "N/A"),
                            "Ability2Cast": abilities_dict.get(
                                "Ability2", {}
                            ).get("display_name", "N/A"),
                            "Ability2CastIcon": abilities_dict.get(
                                "Ability2", {}
                            ).get("display_icon", "N/A"),
                            "UltimateCast": abilities_dict.get(
                                "Ultimate", {}
                            ).get("display_name", "N/A"),
                            "UltimateCastIcon": abilities_dict.get(
                                "Ultimate", {}
                            ).get("display_icon", "N/A"),
                        }

                        # Add the abilities to the row (for merging later)
                        abilities_data.append(
                            {
                                "player_id": row["subject"],
                                **row_abilities,  # Add the ability columns to the row
                            }
                        )

            except Exception as e:
                print(f"Error parsing JSON: {e}")
                print(f"Response content: {response.text}")
        else:
            print(
                f"Failed to fetch data from API. Status code: {response.status_code}"
            )

    # If no abilities data was collected, return the original DataFrame
    if not abilities_data:
        print("No abilities data found.")
        return player_stats_df

    # Convert the list of abilities into a DataFrame
    abilities_df = pd.DataFrame(abilities_data)

    # Merge the abilities data with the player_stats_df on player_id
    player_stats_df = player_stats_df.merge(
        abilities_df, left_on="subject", right_on="player_id", how="left"
    )

    # Drop the player_id column as it is no longer needed after merging
    player_stats_df = player_stats_df.drop(columns=["player_id"])

    return player_stats_df


async def update_weapon_and_ability_names(df):
    """
    Updates the DataFrame with weapon or ability display names and icons.

    Args:
        df (pd.DataFrame): The DataFrame containing 'finishingDamage' and 'killerAgent' columns.

    Returns:
        pd.DataFrame: Updated DataFrame with 'displayName' and 'displayIcon' columns.
    """
    display_names = []
    display_icons = []

    for _, row in df.iterrows():
        damage_item = ""
        if "finishingDamage" in row and isinstance(
            row["finishingDamage"], dict
        ):
            damage_item = str(
                row["finishingDamage"].get("damageItem", "")
            ).lower()

        killer_agent = str(row.get("killerAgent", "Unknown"))  # Agent name

        weapon_info = (
            await get_weapon_data(damage_item) if damage_item else None
        )

        if isinstance(weapon_info, dict):
            # If it's a weapon, store weapon data
            display_names.append(weapon_info.get("displayName", None))
            display_icons.append(weapon_info.get("displayIcon", None))
        else:
            # If it's not a weapon, assume it's an ability and fetch agent data
            ability_info = (
                await get_agent_ability_data(killer_agent, damage_item)
                if damage_item
                else None
            )

            if isinstance(ability_info, dict):
                display_names.append(ability_info.get("displayName", None))
                display_icons.append(ability_info.get("displayIcon", None))
            else:
                # If no weapon or ability found, set as None
                display_names.append(None)
                display_icons.append(None)

    df["displayName"] = display_names
    df["displayIcon"] = display_icons  # Add icon column
    return df


async def extract_round_player_stats(match_data):
    """
    Extracts detailed player statistics per round, including kills, deaths, assists,
    aggregated damage, and cumulative headshot percentage (HS%) for each player across the game.

    Args:
        match_data (dict): The match data containing round and player statistics.

    Returns:
        pd.DataFrame: A dataframe containing detailed player statistics for each round.
    """
    round_stats = []

    # Track cumulative stats for HS% calculation
    cumulative_headshots = {}
    cumulative_bodyshots = {}
    cumulative_legshots = {}

    for round_result in match_data.get("roundResults", []):
        round_num = round_result.get("roundNum")

        for player_stat in round_result.get("playerStats", []):
            player_id = player_stat.get("subject")
            kills = len(player_stat.get("kills", []))
            deaths = player_stat.get("deaths", 0)
            assists = len(player_stat.get("assists", []))

            # Ability casts
            ability_casts = player_stat.get("abilityCasts", {})
            grenade_casts = ability_casts.get("grenadeCasts", 0)
            ability1_casts = ability_casts.get("ability1Casts", 0)
            ability2_casts = ability_casts.get("ability2Casts", 0)
            ultimate_casts = ability_casts.get("ultimateCasts", 0)

            # Damage tracking
            total_damage = 0
            total_headshots = 0
            total_bodyshots = 0
            total_legshots = 0

            for damage_event in player_stat.get("damage", []):
                total_damage += damage_event.get("damage", 0)
                total_headshots += damage_event.get("headshots", 0)
                total_bodyshots += damage_event.get("bodyshots", 0)
                total_legshots += damage_event.get("legshots", 0)

            # Initialize cumulative tracking if player is new
            if player_id not in cumulative_headshots:
                cumulative_headshots[player_id] = 0
                cumulative_bodyshots[player_id] = 0
                cumulative_legshots[player_id] = 0

            # Update cumulative tracking
            cumulative_headshots[player_id] += total_headshots
            cumulative_bodyshots[player_id] += total_bodyshots
            cumulative_legshots[player_id] += total_legshots

            # Calculate cumulative HS% (Headshot %)
            total_shots = (
                cumulative_headshots[player_id]
                + cumulative_bodyshots[player_id]
                + cumulative_legshots[player_id]
            )
            hs_percentage = (
                (cumulative_headshots[player_id] / total_shots) * 100
                if total_shots > 0
                else 0
            )

            # Store round stats
            round_stats.append(
                {
                    "round": round_num,
                    "player_id": player_id,
                    "kills": kills,
                    "deaths": deaths,
                    "assists": assists,
                    "damage_dealt": total_damage,
                    "headshots": total_headshots,
                    "bodyshots": total_bodyshots,
                    "legshots": total_legshots,
                    "hs_percentage": hs_percentage,
                    "grenade_casts": grenade_casts,
                    "ability1_casts": ability1_casts,
                    "ability2_casts": ability2_casts,
                    "ultimate_casts": ultimate_casts,
                }
            )

    return pd.DataFrame(round_stats)


async def extract_round_player_economy(match_data):
    """
    Extracts detailed player economy data per round, including loadout value, spent amount,
    remaining credits, armor, weapon used, and player scores for each player across the game.

    Args:
        match_data (dict): The match data containing round and player economy information.

    Returns:
        pd.DataFrame: A dataframe containing detailed player economy statistics for each round.
    """
    round_economy_stats = []

    for round_result in match_data.get("roundResults", []):
        round_num = round_result.get("roundNum")
        player_scores = {
            score["subject"]: score.get("score", 0)
            for score in round_result.get("playerScores", [])
        }

        for player_economy in round_result.get("playerEconomies", []):
            player_id = player_economy.get("subject")
            loadout_value = player_economy.get("loadoutValue", 0)
            weapon = player_economy.get("weapon", "None")
            armor = player_economy.get("armor", "None")
            remaining = player_economy.get("remaining", 0)
            spent = player_economy.get("spent", 0)
            player_score = player_scores.get(player_id, 0)

            round_economy_stats.append(
                {
                    "round": round_num,
                    "player_id": player_id,
                    "loadout_value": loadout_value,
                    "weapon": weapon,
                    "armor": armor,
                    "remaining_credits": remaining,
                    "spent_credits": spent,
                    "player_score": player_score,
                }
            )

    return pd.DataFrame(round_economy_stats)


def get_agent_name(df, column="subject"):
    """
    Maps the player UUIDs in the specified column to agent names based on the cached agent data.

    Args:
        df (pd.DataFrame): The DataFrame containing the player UUIDs.
        column (str): The column name in the DataFrame to update with agent names.

    Returns:
        pd.DataFrame: The updated DataFrame with agent names in the specified column.
    """
    # Map the player UUIDs to agent names using the agent_cache
    df[column] = df[column].map(
        lambda uuid: agent_cache.get(uuid, {}).get("name", uuid)
    )

    return df


async def get_agent_icon(url: str, zoom_factor: float = 0.15):
    """
    Downloads the agent icon from a URL and converts it into a format suitable for matplotlib.

    Args:
        url (str): The URL of the agent's icon.
        zoom_factor (float, optional): The zoom factor for displaying the icon. Defaults to 0.15.

    Returns:
        OffsetImage: The processed agent icon image.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        img_array = np.array(img)
        return OffsetImage(img_array, zoom=zoom_factor)

    return None  # Handle the case where the image fails to load


async def main(match_id, shard):
    """
    Main function to process match data and return relevant statistics.

    Args:
        match_id (str): The ID of the match.
        shard (str): The shard information for the match.

    Returns:
        tuple: A tuple containing the processed match data,
        player statistics, economy data, match info, and map callouts.
    """
    (
        match_data,
        kill_data,
        match_info,
        map_callouts,
        economy_df,
        defuse_df,
    ) = await process_match(match_id, shard)

    kill_data = kill_data.sort_values("gameTime", ascending=True).reset_index(
        drop=True
    )

    kill_data["killerLocation"] = kill_data.apply(
        extract_killer_location, axis=1
    )

    # Preload map image and normalisation parameters for efficiency
    map_image = load_map_image(match_info)
    norm_params = extract_normalization_params(match_info)

    coordinate_columns = [
        "victimLocation",
        "killerLocation",
        "playerLocations",
    ]
    kill_data = kill_data.apply(
        lambda row: normalize_coordinates_for_df(
            row, map_image, norm_params, coordinate_columns
        ),
        axis=1,
    )

    # Continue processing
    player_stats_df = await get_player_data(match_id, shard)

    kill_data = await get_player_name(kill_data, match_data, "killer")
    kill_data = await get_player_name(kill_data, match_data, "victim")

    economy_df = await get_player_name(economy_df, match_data, "player_id")

    player_stats_df = await get_player_name(
        player_stats_df, match_data, "subject"
    )
    player_stats_df = await get_abilities(player_stats_df)
    player_stats_df = get_agent_name(player_stats_df, column="characterId")

    kill_data = await update_weapon_and_ability_names(kill_data)
    economy_df = await update_economy_display_names(economy_df)

    return (
        kill_data,
        player_stats_df,
        economy_df,
        map_callouts,
        match_info,
        defuse_df,
    )
