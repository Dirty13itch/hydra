"""
Background Scene Generator for Empire of Broken Queens

Generates visual novel background scenes with:
- Location-to-prompt mappings for all game locations
- Time-of-day variations (day, night, dawn, dusk, etc.)
- Weather variations (clear, rain, snow, fog, etc.)
- Mood/atmosphere settings
- Integration with ComfyUI for image generation
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .comfyui_client import ComfyUIClient

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class TimeOfDay(str, Enum):
    """Time of day for scene lighting."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Weather(str, Enum):
    """Weather conditions for scenes."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    MIST = "mist"


class Mood(str, Enum):
    """Atmospheric mood for scenes."""
    PEACEFUL = "peaceful"
    ROMANTIC = "romantic"
    MYSTERIOUS = "mysterious"
    TENSE = "tense"
    OMINOUS = "ominous"
    MELANCHOLIC = "melancholic"
    JOYFUL = "joyful"
    MAJESTIC = "majestic"
    INTIMATE = "intimate"
    DESOLATE = "desolate"


class LocationCategory(str, Enum):
    """Categories of locations."""
    PALACE = "palace"
    OUTDOOR = "outdoor"
    URBAN = "urban"
    NATURE = "nature"
    DUNGEON = "dungeon"
    SPECIAL = "special"


@dataclass
class LocationDefinition:
    """Definition of a scene location with prompt components."""
    id: str
    name: str
    category: LocationCategory
    base_prompt: str
    architectural_style: str = ""
    default_mood: Mood = Mood.PEACEFUL
    indoor: bool = True
    features: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "base_prompt": self.base_prompt,
            "architectural_style": self.architectural_style,
            "default_mood": self.default_mood.value,
            "indoor": self.indoor,
            "features": self.features,
            "color_palette": self.color_palette,
        }


# =============================================================================
# LOCATION DATABASE
# =============================================================================

LOCATIONS: Dict[str, LocationDefinition] = {
    # PALACE LOCATIONS
    "throne_room": LocationDefinition(
        id="throne_room",
        name="Throne Room",
        category=LocationCategory.PALACE,
        base_prompt="grand throne room, ornate throne on raised dais, marble columns, red velvet carpet, golden chandeliers, stained glass windows, royal banners",
        architectural_style="gothic fantasy palace",
        default_mood=Mood.MAJESTIC,
        features=["throne", "columns", "banners", "chandeliers"],
        color_palette=["gold", "crimson", "royal purple", "marble white"],
    ),
    "queens_chamber": LocationDefinition(
        id="queens_chamber",
        name="Queen's Private Chamber",
        category=LocationCategory.PALACE,
        base_prompt="luxurious royal bedroom, ornate four-poster bed with silk canopy, vanity mirror with golden frame, fireplace, velvet curtains, romantic atmosphere",
        architectural_style="baroque royal chamber",
        default_mood=Mood.INTIMATE,
        features=["canopy bed", "vanity", "fireplace", "curtains"],
        color_palette=["burgundy", "gold", "cream", "rose"],
    ),
    "council_chamber": LocationDefinition(
        id="council_chamber",
        name="Royal Council Chamber",
        category=LocationCategory.PALACE,
        base_prompt="circular council chamber, round table with carved throne chairs, maps on walls, burning braziers, high vaulted ceiling, serious atmosphere",
        architectural_style="medieval council room",
        default_mood=Mood.TENSE,
        features=["round table", "chairs", "maps", "braziers"],
        color_palette=["dark wood", "bronze", "parchment", "shadow"],
    ),
    "grand_ballroom": LocationDefinition(
        id="grand_ballroom",
        name="Grand Ballroom",
        category=LocationCategory.PALACE,
        base_prompt="magnificent ballroom, crystal chandeliers, polished marble floor, mirrors on walls, orchestra balcony, tall windows with flowing curtains",
        architectural_style="rococo ballroom",
        default_mood=Mood.JOYFUL,
        features=["chandeliers", "mirrors", "dance floor", "balcony"],
        color_palette=["crystal", "gold", "white", "soft pink"],
    ),
    "palace_library": LocationDefinition(
        id="palace_library",
        name="Royal Library",
        category=LocationCategory.PALACE,
        base_prompt="vast library with towering bookshelves, rolling ladders, reading alcoves, globe and astrolabe, leather armchairs, warm candlelight",
        architectural_style="grand library",
        default_mood=Mood.MYSTERIOUS,
        features=["bookshelves", "ladders", "alcoves", "candles"],
        color_palette=["leather brown", "parchment", "candlelight amber", "dark wood"],
    ),
    "palace_garden": LocationDefinition(
        id="palace_garden",
        name="Palace Gardens",
        category=LocationCategory.OUTDOOR,
        base_prompt="manicured royal gardens, rose hedges, marble fountains, stone pathways, topiary sculptures, flowering arbors, distant palace spires",
        architectural_style="formal french garden",
        default_mood=Mood.ROMANTIC,
        indoor=False,
        features=["fountains", "roses", "hedges", "arbors"],
        color_palette=["green", "rose pink", "white marble", "sky blue"],
    ),
    "palace_balcony": LocationDefinition(
        id="palace_balcony",
        name="Palace Balcony",
        category=LocationCategory.PALACE,
        base_prompt="ornate palace balcony, stone balustrade, view of kingdom below, distant mountains, potted flowers, romantic evening setting",
        architectural_style="renaissance balcony",
        default_mood=Mood.ROMANTIC,
        indoor=False,
        features=["balustrade", "kingdom view", "flowers", "archway"],
        color_palette=["sunset orange", "twilight blue", "stone grey", "gold"],
    ),

    # DUNGEON LOCATIONS
    "dungeon_cell": LocationDefinition(
        id="dungeon_cell",
        name="Dungeon Cell",
        category=LocationCategory.DUNGEON,
        base_prompt="dark dungeon cell, iron bars, chains on stone walls, straw on floor, small barred window, dripping water, dim torchlight",
        architectural_style="medieval dungeon",
        default_mood=Mood.DESOLATE,
        features=["iron bars", "chains", "torch", "straw"],
        color_palette=["dark grey", "rust", "sickly yellow", "black"],
    ),
    "torture_chamber": LocationDefinition(
        id="torture_chamber",
        name="Interrogation Chamber",
        category=LocationCategory.DUNGEON,
        base_prompt="stone interrogation room, restraint devices, iron maiden in corner, brazier with tools, single spotlight from above",
        architectural_style="medieval dungeon",
        default_mood=Mood.OMINOUS,
        features=["devices", "brazier", "chains", "shadows"],
        color_palette=["iron grey", "blood red", "fire orange", "black"],
    ),

    # NATURE LOCATIONS
    "enchanted_forest": LocationDefinition(
        id="enchanted_forest",
        name="Enchanted Forest",
        category=LocationCategory.NATURE,
        base_prompt="magical forest clearing, ancient twisted trees with glowing moss, fireflies, mushroom circles, soft ethereal light filtering through canopy",
        architectural_style="fairy tale forest",
        default_mood=Mood.MYSTERIOUS,
        indoor=False,
        features=["ancient trees", "fireflies", "mushrooms", "mist"],
        color_palette=["emerald green", "fairy glow", "moss", "twilight purple"],
    ),
    "moonlit_lake": LocationDefinition(
        id="moonlit_lake",
        name="Moonlit Lake",
        category=LocationCategory.NATURE,
        base_prompt="serene lake reflecting moonlight, weeping willows along shore, lily pads, distant mountains, stars in clear sky",
        architectural_style="natural landscape",
        default_mood=Mood.ROMANTIC,
        indoor=False,
        features=["lake", "willows", "moon reflection", "lilies"],
        color_palette=["moonlight silver", "deep blue", "willow green", "star white"],
    ),
    "mountain_overlook": LocationDefinition(
        id="mountain_overlook",
        name="Mountain Overlook",
        category=LocationCategory.NATURE,
        base_prompt="dramatic mountain cliff overlook, vast kingdom visible below, wind-swept grasses, ancient stone marker, eagles soaring",
        architectural_style="natural landscape",
        default_mood=Mood.MAJESTIC,
        indoor=False,
        features=["cliff edge", "vista", "stone marker", "eagles"],
        color_palette=["mountain grey", "sky blue", "grass green", "cloud white"],
    ),

    # URBAN LOCATIONS
    "tavern_interior": LocationDefinition(
        id="tavern_interior",
        name="Tavern Interior",
        category=LocationCategory.URBAN,
        base_prompt="cozy medieval tavern, wooden beams, roaring fireplace, bar with bottles, worn wooden tables, lantern light, cozy atmosphere",
        architectural_style="medieval tavern",
        default_mood=Mood.PEACEFUL,
        features=["fireplace", "bar", "tables", "lanterns"],
        color_palette=["warm wood", "fire glow", "amber", "dark brown"],
    ),
    "market_square": LocationDefinition(
        id="market_square",
        name="Market Square",
        category=LocationCategory.URBAN,
        base_prompt="bustling medieval market square, colorful vendor stalls, cobblestone ground, fountain centerpiece, timber-framed buildings",
        architectural_style="medieval town",
        default_mood=Mood.JOYFUL,
        indoor=False,
        features=["stalls", "fountain", "cobblestones", "buildings"],
        color_palette=["cobblestone grey", "colorful fabrics", "timber brown", "sky blue"],
    ),
    "temple_interior": LocationDefinition(
        id="temple_interior",
        name="Temple Interior",
        category=LocationCategory.SPECIAL,
        base_prompt="sacred temple interior, altar with eternal flame, stained glass depicting goddesses, incense smoke, reverent atmosphere",
        architectural_style="fantasy cathedral",
        default_mood=Mood.MYSTERIOUS,
        features=["altar", "stained glass", "flame", "incense"],
        color_palette=["sacred gold", "incense grey", "stained glass colors", "shadow"],
    ),
    "secret_passage": LocationDefinition(
        id="secret_passage",
        name="Secret Passage",
        category=LocationCategory.DUNGEON,
        base_prompt="narrow stone passage, cobwebs, flickering torches, mysterious symbols on walls, hidden door visible, dusty floor",
        architectural_style="hidden tunnel",
        default_mood=Mood.MYSTERIOUS,
        features=["torches", "cobwebs", "symbols", "hidden door"],
        color_palette=["dark stone", "torch orange", "cobweb grey", "mystery purple"],
    ),
    "war_room": LocationDefinition(
        id="war_room",
        name="War Room",
        category=LocationCategory.PALACE,
        base_prompt="strategic war room, large table with kingdom map and figurines, battle plans on walls, armor stands, serious military atmosphere",
        architectural_style="medieval command center",
        default_mood=Mood.TENSE,
        features=["war table", "map", "figurines", "armor"],
        color_palette=["iron grey", "map parchment", "banner red", "candlelight"],
    ),
    "hot_spring": LocationDefinition(
        id="hot_spring",
        name="Hot Spring Bath",
        category=LocationCategory.SPECIAL,
        base_prompt="natural hot spring surrounded by rocks, steam rising, bamboo privacy screens, cherry blossoms, lanterns, sensual atmosphere",
        architectural_style="japanese onsen",
        default_mood=Mood.INTIMATE,
        indoor=False,
        features=["steam", "rocks", "screens", "lanterns"],
        color_palette=["steam white", "rock grey", "cherry pink", "warm lantern"],
    ),
}


# =============================================================================
# PROMPT MODIFIERS
# =============================================================================

TIME_OF_DAY_MODIFIERS: Dict[TimeOfDay, Dict[str, str]] = {
    TimeOfDay.DAWN: {
        "lighting": "soft pink and orange dawn light, first rays of sun",
        "sky": "gradient sky from deep blue to pink and gold",
        "shadows": "long soft shadows stretching westward",
        "atmosphere": "fresh morning mist, dewdrops, awakening",
    },
    TimeOfDay.MORNING: {
        "lighting": "bright warm morning sunlight, golden hour",
        "sky": "clear blue sky with white clouds",
        "shadows": "moderate shadows, warm tones",
        "atmosphere": "crisp clear air, birds singing",
    },
    TimeOfDay.NOON: {
        "lighting": "bright overhead sunlight, strong illumination",
        "sky": "bright blue sky, scattered clouds",
        "shadows": "short sharp shadows directly below",
        "atmosphere": "clear visibility, vibrant colors",
    },
    TimeOfDay.AFTERNOON: {
        "lighting": "warm afternoon light, slightly golden",
        "sky": "blue sky with building clouds",
        "shadows": "lengthening shadows to the east",
        "atmosphere": "relaxed peaceful warmth",
    },
    TimeOfDay.DUSK: {
        "lighting": "rich golden hour light, long dramatic shadows",
        "sky": "orange and purple sunset, dramatic clouds",
        "shadows": "long purple shadows stretching eastward",
        "atmosphere": "romantic golden glow, day ending",
    },
    TimeOfDay.EVENING: {
        "lighting": "dim blue hour light, first stars appearing",
        "sky": "deep blue to purple gradient, venus visible",
        "shadows": "soft diffused shadows, low contrast",
        "atmosphere": "quiet transition, lamplighting time",
    },
    TimeOfDay.NIGHT: {
        "lighting": "moonlight and starlight, silver illumination",
        "sky": "dark blue night sky filled with stars, moon",
        "shadows": "deep shadows with silver highlights",
        "atmosphere": "quiet mysterious darkness, owl hooting",
    },
    TimeOfDay.MIDNIGHT: {
        "lighting": "very dim, only moonlight or torches",
        "sky": "pitch black sky with stars, crescent moon",
        "shadows": "deep impenetrable shadows",
        "atmosphere": "silent still darkness, secrets",
    },
}

WEATHER_MODIFIERS: Dict[Weather, Dict[str, str]] = {
    Weather.CLEAR: {
        "sky_condition": "clear sky",
        "visibility": "perfect visibility",
        "atmosphere": "crisp clean air",
    },
    Weather.CLOUDY: {
        "sky_condition": "partly cloudy sky, scattered clouds",
        "visibility": "good visibility",
        "atmosphere": "mild temperature, diffused light",
    },
    Weather.OVERCAST: {
        "sky_condition": "heavy grey overcast clouds",
        "visibility": "slightly reduced visibility",
        "atmosphere": "flat lighting, muted colors, somber mood",
    },
    Weather.RAIN: {
        "sky_condition": "grey rainy sky",
        "visibility": "rain streaks, wet surfaces",
        "atmosphere": "raindrops, puddles, reflective wet ground",
    },
    Weather.HEAVY_RAIN: {
        "sky_condition": "dark stormy sky, heavy rainfall",
        "visibility": "reduced visibility, sheets of rain",
        "atmosphere": "torrential downpour, flooded streets, dramatic",
    },
    Weather.STORM: {
        "sky_condition": "dark thunderstorm clouds, lightning flashes",
        "visibility": "poor visibility, dramatic lightning",
        "atmosphere": "thunder, wind, dramatic storm, chaotic energy",
    },
    Weather.SNOW: {
        "sky_condition": "grey winter sky, falling snowflakes",
        "visibility": "snowfall reducing visibility",
        "atmosphere": "snow-covered surfaces, peaceful winter, cold",
    },
    Weather.FOG: {
        "sky_condition": "thick fog obscuring sky",
        "visibility": "very low visibility, mysterious",
        "atmosphere": "eerie fog, shapes emerging, mysterious",
    },
    Weather.MIST: {
        "sky_condition": "light mist, diffused sunlight",
        "visibility": "soft diffused visibility",
        "atmosphere": "gentle mist, romantic softness, ethereal",
    },
}

MOOD_MODIFIERS: Dict[Mood, Dict[str, str]] = {
    Mood.PEACEFUL: {
        "atmosphere": "calm serene peaceful atmosphere",
        "colors": "soft warm harmonious colors",
        "feeling": "tranquil comfortable safe",
    },
    Mood.ROMANTIC: {
        "atmosphere": "romantic intimate atmosphere, soft focus",
        "colors": "warm rose and gold tones",
        "feeling": "love passion tenderness",
    },
    Mood.MYSTERIOUS: {
        "atmosphere": "mysterious enigmatic atmosphere",
        "colors": "deep purples and shadowy tones",
        "feeling": "secrets hidden unknown intriguing",
    },
    Mood.TENSE: {
        "atmosphere": "tense dramatic atmosphere",
        "colors": "high contrast stark lighting",
        "feeling": "suspense anticipation danger",
    },
    Mood.OMINOUS: {
        "atmosphere": "dark ominous foreboding atmosphere",
        "colors": "dark threatening shadows, red accents",
        "feeling": "dread fear impending doom",
    },
    Mood.MELANCHOLIC: {
        "atmosphere": "melancholic sad atmosphere",
        "colors": "muted blues and greys, desaturated",
        "feeling": "sorrow loss longing",
    },
    Mood.JOYFUL: {
        "atmosphere": "bright joyful celebratory atmosphere",
        "colors": "vibrant warm cheerful colors",
        "feeling": "happiness celebration life",
    },
    Mood.MAJESTIC: {
        "atmosphere": "grand majestic impressive atmosphere",
        "colors": "rich royal colors, gold accents",
        "feeling": "awe power grandeur",
    },
    Mood.INTIMATE: {
        "atmosphere": "intimate private cozy atmosphere",
        "colors": "warm soft candlelit tones",
        "feeling": "closeness warmth privacy",
    },
    Mood.DESOLATE: {
        "atmosphere": "desolate abandoned hopeless atmosphere",
        "colors": "grey brown washed out colors",
        "feeling": "emptiness abandonment despair",
    },
}


# =============================================================================
# SCENE GENERATION
# =============================================================================

class SceneGenerator:
    """Generate background scenes with location-aware prompts."""

    def __init__(self, comfyui_url: Optional[str] = None):
        self.comfyui = ComfyUIClient(comfyui_url)
        self.output_dir = Path(os.environ.get("SCENE_OUTPUT_DIR", "/data/scenes"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_location(self, location_id: str) -> Optional[LocationDefinition]:
        """Get a location by ID."""
        return LOCATIONS.get(location_id)

    def list_locations(self) -> List[Dict[str, Any]]:
        """List all available locations."""
        return [loc.to_dict() for loc in LOCATIONS.values()]

    def list_locations_by_category(self, category: LocationCategory) -> List[Dict[str, Any]]:
        """List locations filtered by category."""
        return [
            loc.to_dict() for loc in LOCATIONS.values()
            if loc.category == category
        ]

    def build_scene_prompt(
        self,
        location_id: str,
        time_of_day: TimeOfDay = TimeOfDay.AFTERNOON,
        weather: Weather = Weather.CLEAR,
        mood: Optional[Mood] = None,
        custom_elements: Optional[List[str]] = None,
    ) -> str:
        """Build a complete scene prompt from components."""
        location = self.get_location(location_id)
        if not location:
            raise ValueError(f"Unknown location: {location_id}")

        # Use location's default mood if not specified
        if mood is None:
            mood = location.default_mood

        # Build prompt components
        prompt_parts = []

        # Base location description
        prompt_parts.append(location.base_prompt)

        # Architectural style
        if location.architectural_style:
            prompt_parts.append(location.architectural_style)

        # Time of day (only for outdoor or mixed scenes)
        time_mods = TIME_OF_DAY_MODIFIERS.get(time_of_day, {})
        if not location.indoor or location_id in ["palace_balcony", "palace_garden"]:
            prompt_parts.append(time_mods.get("lighting", ""))
            prompt_parts.append(time_mods.get("sky", ""))
        prompt_parts.append(time_mods.get("atmosphere", ""))

        # Weather (only for outdoor scenes)
        if not location.indoor:
            weather_mods = WEATHER_MODIFIERS.get(weather, {})
            prompt_parts.append(weather_mods.get("sky_condition", ""))
            prompt_parts.append(weather_mods.get("atmosphere", ""))

        # Mood modifiers
        mood_mods = MOOD_MODIFIERS.get(mood, {})
        prompt_parts.append(mood_mods.get("atmosphere", ""))
        prompt_parts.append(mood_mods.get("colors", ""))

        # Custom elements
        if custom_elements:
            prompt_parts.extend(custom_elements)

        # Standard quality tags
        prompt_parts.extend([
            "visual novel background",
            "no characters",
            "no people",
            "detailed environment",
            "anime style",
            "painterly",
            "high detail",
            "volumetric lighting",
            "masterpiece quality"
        ])

        # Filter empty strings and join
        prompt = ", ".join(p for p in prompt_parts if p.strip())
        return prompt

    def generate_scene(
        self,
        location_id: str,
        time_of_day: TimeOfDay = TimeOfDay.AFTERNOON,
        weather: Weather = Weather.CLEAR,
        mood: Optional[Mood] = None,
        custom_elements: Optional[List[str]] = None,
        scene_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a scene background image."""
        if scene_id is None:
            scene_id = f"{location_id}_{time_of_day.value}_{uuid.uuid4().hex[:8]}"

        prompt = self.build_scene_prompt(
            location_id=location_id,
            time_of_day=time_of_day,
            weather=weather,
            mood=mood,
            custom_elements=custom_elements,
        )

        # Queue to ComfyUI
        prompt_id = self.comfyui.generate_background(
            scene_description=prompt,
            time_of_day=time_of_day.value,
            scene_id=scene_id,
        )

        return {
            "status": "queued",
            "prompt_id": prompt_id,
            "scene_id": scene_id,
            "location_id": location_id,
            "time_of_day": time_of_day.value,
            "weather": weather.value,
            "mood": mood.value if mood else None,
            "prompt": prompt,
        }

    def generate_time_variations(
        self,
        location_id: str,
        times: Optional[List[TimeOfDay]] = None,
        weather: Weather = Weather.CLEAR,
        mood: Optional[Mood] = None,
    ) -> List[Dict[str, Any]]:
        """Generate a location at multiple times of day."""
        if times is None:
            times = [TimeOfDay.MORNING, TimeOfDay.AFTERNOON, TimeOfDay.DUSK, TimeOfDay.NIGHT]

        results = []
        for time in times:
            result = self.generate_scene(
                location_id=location_id,
                time_of_day=time,
                weather=weather,
                mood=mood,
            )
            results.append(result)

        return results

    def generate_weather_variations(
        self,
        location_id: str,
        weathers: Optional[List[Weather]] = None,
        time_of_day: TimeOfDay = TimeOfDay.AFTERNOON,
        mood: Optional[Mood] = None,
    ) -> List[Dict[str, Any]]:
        """Generate a location with different weather conditions."""
        location = self.get_location(location_id)
        if location and location.indoor:
            # Indoor locations don't need weather variations
            return [self.generate_scene(
                location_id=location_id,
                time_of_day=time_of_day,
                mood=mood,
            )]

        if weathers is None:
            weathers = [Weather.CLEAR, Weather.CLOUDY, Weather.RAIN, Weather.FOG]

        results = []
        for weather in weathers:
            result = self.generate_scene(
                location_id=location_id,
                time_of_day=time_of_day,
                weather=weather,
                mood=mood,
            )
            results.append(result)

        return results


# =============================================================================
# API ROUTER
# =============================================================================

def create_scene_backgrounds_router() -> APIRouter:
    """Create FastAPI router for scene background generation."""
    router = APIRouter(prefix="/scenes", tags=["scenes"])
    generator = SceneGenerator()

    # Request models
    class GenerateSceneRequest(BaseModel):
        location_id: str = Field(..., description="Location ID from the location database")
        time_of_day: TimeOfDay = Field(TimeOfDay.AFTERNOON, description="Time of day for lighting")
        weather: Weather = Field(Weather.CLEAR, description="Weather condition")
        mood: Optional[Mood] = Field(None, description="Override mood (defaults to location's mood)")
        custom_elements: Optional[List[str]] = Field(None, description="Additional prompt elements")
        scene_id: Optional[str] = Field(None, description="Custom scene ID for output")

    class BatchSceneRequest(BaseModel):
        location_id: str
        times: Optional[List[TimeOfDay]] = None
        weathers: Optional[List[Weather]] = None
        mood: Optional[Mood] = None

    class PromptPreviewRequest(BaseModel):
        location_id: str
        time_of_day: TimeOfDay = TimeOfDay.AFTERNOON
        weather: Weather = Weather.CLEAR
        mood: Optional[Mood] = None
        custom_elements: Optional[List[str]] = None

    @router.get("/locations")
    async def list_locations(category: Optional[LocationCategory] = None):
        """List all available scene locations."""
        if category:
            locations = generator.list_locations_by_category(category)
        else:
            locations = generator.list_locations()

        return {
            "count": len(locations),
            "locations": locations,
        }

    @router.get("/locations/{location_id}")
    async def get_location(location_id: str):
        """Get details for a specific location."""
        location = generator.get_location(location_id)
        if not location:
            raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")
        return location.to_dict()

    @router.get("/modifiers")
    async def get_modifiers():
        """Get all available modifiers (time, weather, mood)."""
        return {
            "times_of_day": [t.value for t in TimeOfDay],
            "weather_conditions": [w.value for w in Weather],
            "moods": [m.value for m in Mood],
            "location_categories": [c.value for c in LocationCategory],
        }

    @router.post("/preview-prompt")
    async def preview_prompt(request: PromptPreviewRequest):
        """Preview the generated prompt without queuing generation."""
        try:
            prompt = generator.build_scene_prompt(
                location_id=request.location_id,
                time_of_day=request.time_of_day,
                weather=request.weather,
                mood=request.mood,
                custom_elements=request.custom_elements,
            )

            location = generator.get_location(request.location_id)

            return {
                "location_id": request.location_id,
                "location_name": location.name if location else "Unknown",
                "time_of_day": request.time_of_day.value,
                "weather": request.weather.value,
                "mood": (request.mood or location.default_mood).value if location else None,
                "prompt": prompt,
                "prompt_length": len(prompt),
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/generate")
    async def generate_scene(request: GenerateSceneRequest):
        """Generate a single scene background."""
        try:
            result = generator.generate_scene(
                location_id=request.location_id,
                time_of_day=request.time_of_day,
                weather=request.weather,
                mood=request.mood,
                custom_elements=request.custom_elements,
                scene_id=request.scene_id,
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/generate/time-variations")
    async def generate_time_variations(request: BatchSceneRequest):
        """Generate a location at multiple times of day."""
        try:
            results = generator.generate_time_variations(
                location_id=request.location_id,
                times=request.times,
                mood=request.mood,
            )
            return {
                "location_id": request.location_id,
                "variations": len(results),
                "scenes": results,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/generate/weather-variations")
    async def generate_weather_variations(request: BatchSceneRequest):
        """Generate a location with different weather conditions."""
        try:
            time = request.times[0] if request.times else TimeOfDay.AFTERNOON
            results = generator.generate_weather_variations(
                location_id=request.location_id,
                weathers=request.weathers,
                time_of_day=time,
                mood=request.mood,
            )
            return {
                "location_id": request.location_id,
                "variations": len(results),
                "scenes": results,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/generate/full-set")
    async def generate_full_location_set(
        location_id: str,
        include_weather: bool = False,
        background_tasks: BackgroundTasks = None,
    ):
        """Generate a complete set of scenes for a location (all times, optionally weather)."""
        location = generator.get_location(location_id)
        if not location:
            raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")

        all_results = []

        # Generate time variations
        times = [TimeOfDay.MORNING, TimeOfDay.AFTERNOON, TimeOfDay.DUSK, TimeOfDay.NIGHT]
        for time in times:
            if include_weather and not location.indoor:
                # For outdoor locations, add weather variations
                weathers = [Weather.CLEAR, Weather.CLOUDY, Weather.RAIN]
                for weather in weathers:
                    result = generator.generate_scene(
                        location_id=location_id,
                        time_of_day=time,
                        weather=weather,
                    )
                    all_results.append(result)
            else:
                result = generator.generate_scene(
                    location_id=location_id,
                    time_of_day=time,
                    weather=Weather.CLEAR,
                )
                all_results.append(result)

        return {
            "location_id": location_id,
            "location_name": location.name,
            "total_scenes": len(all_results),
            "scenes": all_results,
        }

    return router
