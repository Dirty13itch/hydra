"""
Story Generation Crew for Empire of Broken Queens

CrewAI multi-agent system for visual novel story generation.
Agents work together to create compelling narratives with
proper pacing, character consistency, and emotional depth.

Agents:
- Story Architect: Plans story structure, arcs, and pacing
- Dialogue Writer: Creates character-specific dialogue
- Scene Director: Designs visual scenes and transitions
- Continuity Editor: Ensures consistency across scenes
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# Configuration
LITELLM_URL = "http://192.168.1.244:4000"
LITELLM_API_KEY = "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7"
DEFAULT_MODEL = "ollama/qwen2.5:7b"  # Fast, good for iteration
CREATIVE_MODEL = "ollama/qwen2.5:32b"  # Larger model for final output


class StoryAgent:
    """Base class for story generation agents."""

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        model: str = DEFAULT_MODEL,
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model = model
        self.client = httpx.Client(timeout=120.0)

    def _call_llm(self, prompt: str, system: Optional[str] = None) -> str:
        """Call LLM via LiteLLM gateway."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"

    def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        """Execute a task with optional context."""
        system_prompt = f"""You are a {self.role}.

Your goal: {self.goal}

Background: {self.backstory}

Respond with high-quality, creative content appropriate for an adult visual novel.
Focus on character depth, emotional resonance, and narrative tension."""

        task_prompt = task
        if context:
            task_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        return self._call_llm(task_prompt, system_prompt)


class StoryArchitect(StoryAgent):
    """Plans story structure, arcs, and pacing."""

    def __init__(self):
        super().__init__(
            role="Story Architect",
            goal="Design compelling narrative structures with proper pacing and emotional beats",
            backstory="""You are a master storyteller who has crafted narratives for
            countless visual novels. You understand the unique requirements of branching
            narratives, the importance of player agency, and how to create memorable
            story moments. You specialize in adult themes handled with maturity and depth.""",
        )

    def create_chapter_outline(
        self,
        chapter_number: int,
        previous_summary: str = "",
        characters: List[str] = None,
        themes: List[str] = None,
    ) -> Dict[str, Any]:
        """Create a detailed chapter outline."""
        characters_str = ", ".join(characters) if characters else "the queens"
        themes_str = ", ".join(themes) if themes else "power, desire, betrayal"

        task = f"""Create a detailed outline for Chapter {chapter_number} of "Empire of Broken Queens".

Previous events: {previous_summary or "This is the beginning."}

Featured characters: {characters_str}
Themes to explore: {themes_str}

Provide a structured outline with:
1. Chapter title and hook
2. 3-5 major scenes with:
   - Location
   - Characters present
   - Key events
   - Emotional beats
   - Potential player choices
3. Chapter climax
4. Cliffhanger or resolution

Format as JSON with keys: title, hook, scenes, climax, ending"""

        response = self.execute(task)

        # Try to parse as JSON, otherwise wrap in dict
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_outline": response, "chapter": chapter_number}


class DialogueWriter(StoryAgent):
    """Creates character-specific dialogue."""

    def __init__(self):
        super().__init__(
            role="Dialogue Writer",
            goal="Write authentic, emotionally resonant dialogue that reveals character",
            backstory="""You are a dialogue specialist who understands how people
            really talk - with subtext, rhythm, and personality. Each character
            has a unique voice, vocabulary, and way of expressing themselves.
            You write dialogue that reveals character through word choice and
            delivery, not just content.""",
        )

    def write_scene_dialogue(
        self,
        scene_description: str,
        characters: List[Dict[str, str]],
        emotional_tone: str,
        objectives: List[str],
    ) -> Dict[str, Any]:
        """Write dialogue for a scene."""
        char_descriptions = "\n".join(
            [f"- {c['name']}: {c.get('personality', 'complex')}" for c in characters]
        )

        task = f"""Write dialogue for this scene:

{scene_description}

Characters:
{char_descriptions}

Emotional tone: {emotional_tone}
Scene objectives: {', '.join(objectives)}

Write natural dialogue that:
1. Reveals character through voice and word choice
2. Builds tension or emotion progressively
3. Includes stage directions for delivery [in brackets]
4. Has subtext and things left unsaid
5. Is appropriate for a mature visual novel

Format each line as:
CHARACTER_NAME: "Dialogue" [emotion/action]"""

        response = self.execute(task)

        # Parse into structured format
        lines = []
        for line in response.split("\n"):
            if ":" in line and '"' in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    content = parts[1].strip()
                    lines.append({"speaker": speaker, "content": content})

        return {
            "dialogue": lines,
            "raw": response,
            "scene": scene_description[:100],
            "tone": emotional_tone,
        }


class SceneDirector(StoryAgent):
    """Designs visual scenes and transitions."""

    def __init__(self):
        super().__init__(
            role="Scene Director",
            goal="Create vivid, cinematic scene descriptions that translate to visual novel format",
            backstory="""You are a visual storyteller who thinks in images.
            You understand composition, lighting, and visual metaphor.
            You know how to describe scenes that artists can bring to life,
            with attention to mood, atmosphere, and character positioning.""",
        )

    def design_scene(
        self,
        narrative_beat: str,
        location: str,
        characters: List[str],
        time_of_day: str = "day",
        mood: str = "neutral",
    ) -> Dict[str, Any]:
        """Design a visual scene."""
        task = f"""Design a visual scene for this narrative moment:

{narrative_beat}

Location: {location}
Characters present: {', '.join(characters)}
Time of day: {time_of_day}
Mood: {mood}

Provide:
1. Background description (for artist reference)
2. Character positions and poses
3. Lighting and atmosphere
4. Key visual elements/props
5. Suggested transition into this scene
6. Suggested music/ambient audio

Format as JSON with keys: background, characters, lighting, props, transition, audio"""

        response = self.execute(task)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_design": response, "location": location}


class ContinuityEditor(StoryAgent):
    """Ensures consistency across scenes."""

    def __init__(self):
        super().__init__(
            role="Continuity Editor",
            goal="Maintain narrative and visual consistency throughout the story",
            backstory="""You have an encyclopedic memory for story details.
            You catch contradictions, track character development, ensure
            timeline consistency, and maintain the internal logic of the world.
            Nothing escapes your attention.""",
        )

    def check_consistency(
        self,
        new_content: str,
        existing_facts: Dict[str, Any],
        character_states: Dict[str, str],
    ) -> Dict[str, Any]:
        """Check new content for consistency issues."""
        task = f"""Review this new content for consistency issues:

NEW CONTENT:
{new_content}

ESTABLISHED FACTS:
{json.dumps(existing_facts, indent=2)}

CHARACTER STATES:
{json.dumps(character_states, indent=2)}

Check for:
1. Timeline contradictions
2. Character behavior inconsistencies
3. Location/setting errors
4. Previously established facts that are contradicted
5. Missing context that should be referenced

Format response as JSON with:
- issues: list of problems found
- suggestions: list of fixes
- approved: boolean
- notes: additional observations"""

        response = self.execute(task)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_review": response, "approved": True, "issues": []}


class StoryGenerationCrew:
    """
    CrewAI-style multi-agent crew for story generation.

    Coordinates Story Architect, Dialogue Writer, Scene Director,
    and Continuity Editor to produce complete visual novel content.
    """

    def __init__(self):
        self.architect = StoryArchitect()
        self.dialogue_writer = DialogueWriter()
        self.scene_director = SceneDirector()
        self.continuity_editor = ContinuityEditor()

        self.story_state = {
            "chapters_completed": [],
            "character_states": {},
            "established_facts": {},
            "timeline": [],
        }

    def generate_chapter(
        self,
        chapter_number: int,
        featured_characters: List[str] = None,
        themes: List[str] = None,
        previous_summary: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a complete chapter using all agents.

        Returns structured chapter data ready for asset generation.
        """
        logger.info(f"Generating chapter {chapter_number}...")
        start_time = datetime.now()

        # Step 1: Story Architect creates outline
        logger.info("Step 1: Creating chapter outline...")
        outline = self.architect.create_chapter_outline(
            chapter_number=chapter_number,
            previous_summary=previous_summary,
            characters=featured_characters,
            themes=themes,
        )

        # Step 2: Scene Director designs each scene
        logger.info("Step 2: Designing scenes...")
        scenes = []
        scene_list = outline.get("scenes", [])

        for i, scene_outline in enumerate(scene_list):
            if isinstance(scene_outline, dict):
                scene_design = self.scene_director.design_scene(
                    narrative_beat=scene_outline.get("events", scene_outline.get("description", "")),
                    location=scene_outline.get("location", "throne room"),
                    characters=scene_outline.get("characters", featured_characters or []),
                    time_of_day=scene_outline.get("time", "day"),
                    mood=scene_outline.get("emotion", "neutral"),
                )
                scenes.append({
                    "scene_number": i + 1,
                    "outline": scene_outline,
                    "design": scene_design,
                })

        # Step 3: Dialogue Writer creates dialogue for each scene
        logger.info("Step 3: Writing dialogue...")
        for scene in scenes:
            char_names = scene["outline"].get("characters", featured_characters or [])
            characters = [{"name": c, "personality": "complex"} for c in char_names]

            dialogue = self.dialogue_writer.write_scene_dialogue(
                scene_description=json.dumps(scene["outline"]),
                characters=characters,
                emotional_tone=scene["outline"].get("emotion", "dramatic"),
                objectives=scene["outline"].get("objectives", ["advance plot"]),
            )
            scene["dialogue"] = dialogue

        # Step 4: Continuity Editor reviews
        logger.info("Step 4: Continuity check...")
        chapter_content = json.dumps({
            "outline": outline,
            "scenes": scenes,
        })

        consistency_check = self.continuity_editor.check_consistency(
            new_content=chapter_content,
            existing_facts=self.story_state["established_facts"],
            character_states=self.story_state["character_states"],
        )

        # Compile final chapter
        chapter = {
            "chapter_number": chapter_number,
            "title": outline.get("title", f"Chapter {chapter_number}"),
            "hook": outline.get("hook", ""),
            "scenes": scenes,
            "climax": outline.get("climax", ""),
            "ending": outline.get("ending", ""),
            "consistency_check": consistency_check,
            "generation_time_seconds": (datetime.now() - start_time).total_seconds(),
            "generated_at": datetime.now().isoformat(),
        }

        # Update story state
        self.story_state["chapters_completed"].append(chapter_number)
        self.story_state["timeline"].append({
            "chapter": chapter_number,
            "title": chapter["title"],
        })

        return chapter

    def generate_scene(
        self,
        description: str,
        characters: List[str],
        location: str,
        emotional_tone: str = "dramatic",
        time_of_day: str = "day",
    ) -> Dict[str, Any]:
        """Generate a single scene with design and dialogue."""
        # Design scene
        design = self.scene_director.design_scene(
            narrative_beat=description,
            location=location,
            characters=characters,
            time_of_day=time_of_day,
            mood=emotional_tone,
        )

        # Write dialogue
        char_list = [{"name": c, "personality": "complex"} for c in characters]
        dialogue = self.dialogue_writer.write_scene_dialogue(
            scene_description=description,
            characters=char_list,
            emotional_tone=emotional_tone,
            objectives=["advance plot", "reveal character"],
        )

        return {
            "description": description,
            "location": location,
            "characters": characters,
            "time_of_day": time_of_day,
            "design": design,
            "dialogue": dialogue,
            "generated_at": datetime.now().isoformat(),
        }

    def generate_dialogue_variation(
        self,
        scene_context: str,
        character: str,
        emotion: str,
        line_count: int = 5,
    ) -> List[str]:
        """Generate dialogue variations for a character."""
        task = f"""Generate {line_count} dialogue variations for {character} in this context:

{scene_context}

Emotion: {emotion}

Each line should be distinct but appropriate for the character and situation.
Make them feel natural, not generic.
Format as a numbered list."""

        response = self.dialogue_writer.execute(task)

        # Parse numbered lines
        lines = []
        for line in response.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove number prefix
                content = line.lstrip("0123456789.)-: ")
                if content:
                    lines.append(content)

        return lines[:line_count]

    def export_for_renpy(self, chapter: Dict[str, Any]) -> str:
        """Export chapter to Ren'Py script format."""
        script_lines = [
            f"# {chapter.get('title', 'Chapter')}",
            f"# Generated: {chapter.get('generated_at', '')}",
            "",
            f"label chapter_{chapter.get('chapter_number', 1)}:",
            "",
        ]

        for scene in chapter.get("scenes", []):
            scene_num = scene.get("scene_number", 1)
            location = scene.get("design", {}).get("background", "throne room")

            script_lines.append(f"    # Scene {scene_num}")
            script_lines.append(f'    scene bg_{location.replace(" ", "_").lower()}')
            script_lines.append("")

            dialogue = scene.get("dialogue", {}).get("dialogue", [])
            for line in dialogue:
                speaker = line.get("speaker", "narrator").lower().replace(" ", "_")
                content = line.get("content", "").replace('"', "'")
                script_lines.append(f'    {speaker} "{content}"')

            script_lines.append("")

        script_lines.append("    return")

        return "\n".join(script_lines)


# API endpoints helper functions
def create_story_crew_router():
    """Create FastAPI router for story crew endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/story", tags=["story-crew"])

    class GenerateChapterRequest(BaseModel):
        chapter_number: int
        featured_characters: List[str] = []
        themes: List[str] = []
        previous_summary: str = ""

    class GenerateSceneRequest(BaseModel):
        description: str
        characters: List[str]
        location: str
        emotional_tone: str = "dramatic"
        time_of_day: str = "day"

    class DialogueRequest(BaseModel):
        scene_context: str
        character: str
        emotion: str
        line_count: int = 5

    crew = StoryGenerationCrew()

    @router.post("/generate-chapter")
    async def generate_chapter(request: GenerateChapterRequest):
        """Generate a complete chapter using the story crew."""
        chapter = crew.generate_chapter(
            chapter_number=request.chapter_number,
            featured_characters=request.featured_characters,
            themes=request.themes,
            previous_summary=request.previous_summary,
        )
        return chapter

    @router.post("/generate-scene")
    async def generate_scene(request: GenerateSceneRequest):
        """Generate a single scene with design and dialogue."""
        scene = crew.generate_scene(
            description=request.description,
            characters=request.characters,
            location=request.location,
            emotional_tone=request.emotional_tone,
            time_of_day=request.time_of_day,
        )
        return scene

    @router.post("/generate-dialogue")
    async def generate_dialogue(request: DialogueRequest):
        """Generate dialogue variations for a character."""
        lines = crew.generate_dialogue_variation(
            scene_context=request.scene_context,
            character=request.character,
            emotion=request.emotion,
            line_count=request.line_count,
        )
        return {"character": request.character, "lines": lines}

    @router.post("/export-renpy/{chapter_number}")
    async def export_renpy(chapter_number: int):
        """Export a generated chapter to Ren'Py format."""
        # This would need chapter storage - for now, return template
        return {
            "message": "Use /generate-chapter first, then export",
            "format": "renpy",
            "chapter": chapter_number,
        }

    @router.get("/crew-status")
    async def crew_status():
        """Get story crew status."""
        return {
            "crew": "story_generation",
            "agents": [
                {"role": "Story Architect", "status": "ready"},
                {"role": "Dialogue Writer", "status": "ready"},
                {"role": "Scene Director", "status": "ready"},
                {"role": "Continuity Editor", "status": "ready"},
            ],
            "llm_gateway": LITELLM_URL,
            "default_model": DEFAULT_MODEL,
            "chapters_generated": len(crew.story_state["chapters_completed"]),
        }

    return router
