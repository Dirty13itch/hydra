-- =============================================================================
-- Empire of Broken Queens - Populate Queens Data
-- Migration: 002_populate_queens.sql
-- Description: Insert all queens with full physical/personality DNA
-- =============================================================================

-- Update existing queens with full DNA data
UPDATE queens SET
    dna = '{
        "physical": {
            "height_inches": 70,
            "height_cm": 179,
            "height_category": "tall",
            "bust_size": "34DD",
            "bust_enhanced": true,
            "waist": 25,
            "hips": 35,
            "body_type": "athletic_elegant",
            "hair_color": "brown",
            "hair_style": "long waves",
            "eye_color": "brown",
            "skin_tone": "porcelain Nordic",
            "skin_features": ["freckled"],
            "ethnicity": "Swedish",
            "age_presentation": "early 30s"
        },
        "personality": {
            "dominance": 8,
            "submission": 3,
            "intelligence": 9,
            "manipulation": 8,
            "loyalty": 4,
            "jealousy": 7,
            "sensuality": 8,
            "aggression": 6,
            "corruption_resistance": 8,
            "corruption_speed": 4,
            "surrender_style": "fighting",
            "accent": "Swedish",
            "speech_patterns": ["formal", "cold", "precise"],
            "public_persona": "Ice Queen CEO",
            "private_persona": "Lonely perfectionist",
            "triggers": ["being challenged", "losing control", "genuine connection"]
        },
        "generation": {
            "base_prompt": "athletic elegant Swedish woman 5ft10, enhanced 34DD breasts high-set prominent, 25in waist hourglass, brown captivating eyes, porcelain Nordic freckled skin, brown long flowing waves hair, Swedish high cheekbones, early 30s",
            "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
        }
    }'::jsonb,
    height = '5''10"',
    measurements = '34DD-25-35',
    body_type = 'athletic elegant',
    eye_color = 'brown',
    skin_tone = 'porcelain Nordic',
    hair_color = 'brown',
    hair_style = 'long waves',
    backstory = 'Former exotic dancer who built a corporate empire through ruthless ambition and strategic seduction. Now CEO of a major fashion conglomerate, she maintains her icy exterior while secretly craving the submission she once performed.'
WHERE name = 'Emilie Ekstrom';

UPDATE queens SET
    dna = '{
        "physical": {
            "height_inches": 67,
            "height_cm": 170,
            "height_category": "average",
            "bust_size": "32DD",
            "bust_enhanced": true,
            "waist": 25,
            "hips": 35,
            "body_type": "toned_athletic",
            "hair_color": "platinum blonde",
            "hair_style": "short edgy",
            "eye_color": "ice blue",
            "skin_tone": "fair",
            "skin_features": ["full sleeve tattoos", "piercings"],
            "ethnicity": "German",
            "age_presentation": "mid 30s"
        },
        "personality": {
            "dominance": 7,
            "submission": 5,
            "intelligence": 7,
            "manipulation": 6,
            "loyalty": 6,
            "jealousy": 5,
            "sensuality": 9,
            "aggression": 7,
            "corruption_resistance": 5,
            "corruption_speed": 7,
            "surrender_style": "sudden",
            "accent": "German",
            "speech_patterns": ["direct", "crude", "playful"],
            "public_persona": "Edgy artist rebel",
            "private_persona": "Secretly wants to be owned",
            "triggers": ["being dominated", "pain play", "public exposure"]
        },
        "generation": {
            "base_prompt": "toned athletic German woman 5ft7, enhanced 32DD breasts prominent, 25in waist hourglass, full sleeve tattoos visible, ice blue piercing eyes, platinum blonde short edgy hair, German sharp features, mid 30s edgy confident",
            "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
        }
    }'::jsonb,
    height = '5''7"',
    measurements = '32DD-25-35',
    body_type = 'toned athletic',
    eye_color = 'ice blue',
    skin_tone = 'fair',
    hair_color = 'platinum blonde',
    hair_style = 'short edgy',
    backstory = 'World-renowned tattoo artist and underground model who moonlights as a high-end escort. Her edgy exterior hides a woman who has never found anyone strong enough to truly dominate her - until now.'
WHERE name = 'Jordan Night';

UPDATE queens SET
    dna = '{
        "physical": {
            "height_inches": 64,
            "height_cm": 163,
            "height_category": "petite",
            "bust_size": "34DD",
            "bust_enhanced": true,
            "waist": 24,
            "hips": 34,
            "body_type": "voluptuous",
            "hair_color": "blonde",
            "hair_style": "long straight",
            "eye_color": "hazel",
            "skin_tone": "olive Mediterranean",
            "skin_features": [],
            "ethnicity": "Ukrainian-Canadian",
            "age_presentation": "early 30s"
        },
        "personality": {
            "dominance": 6,
            "submission": 6,
            "intelligence": 7,
            "manipulation": 8,
            "loyalty": 5,
            "jealousy": 8,
            "sensuality": 9,
            "aggression": 5,
            "corruption_resistance": 4,
            "corruption_speed": 6,
            "surrender_style": "gradual",
            "accent": "Slavic hint",
            "speech_patterns": ["sultry", "commanding", "seductive"],
            "public_persona": "Industry royalty",
            "private_persona": "Craves being truly desired",
            "triggers": ["genuine admiration", "being prioritized", "jealousy games"]
        },
        "generation": {
            "base_prompt": "voluptuous Ukrainian woman 5ft4, enhanced 34DD very large breasts prominent cleavage, 24in waist dramatic hourglass, hazel sultry eyes, olive Mediterranean skin, blonde long straight hair, Slavic regal features, early 30s commanding",
            "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
        }
    }'::jsonb,
    height = '5''4"',
    measurements = '34DD-24-34',
    body_type = 'voluptuous',
    eye_color = 'hazel',
    skin_tone = 'olive Mediterranean',
    hair_color = 'blonde',
    hair_style = 'long straight',
    backstory = 'Adult industry legend who parlayed her fame into business ownership and media appearances. Despite her confident public persona, she secretly yearns to find someone who sees past the fantasy to the real woman beneath.'
WHERE name = 'Nikki Benz';

-- Insert remaining queens
INSERT INTO queens (name, codename, tier, height, measurements, body_type, eye_color, skin_tone, hair_color, hair_style, dna, backstory)
VALUES
-- ELITE TIER
('Puma Swede', 'Amazon Goddess', 'Elite', '5''10"', '34F-25-36', 'amazon', 'blue', 'fair Nordic', 'blonde', 'long', '{
    "physical": {
        "height_inches": 70,
        "height_cm": 178,
        "height_category": "tall",
        "bust_size": "34F",
        "bust_enhanced": true,
        "waist": 25,
        "hips": 36,
        "body_type": "amazon",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "blue",
        "skin_tone": "fair Nordic",
        "skin_features": [],
        "ethnicity": "Swedish-Finnish",
        "age_presentation": "late 30s"
    },
    "personality": {
        "dominance": 8,
        "submission": 4,
        "intelligence": 6,
        "manipulation": 5,
        "loyalty": 7,
        "jealousy": 6,
        "sensuality": 9,
        "aggression": 7,
        "corruption_resistance": 5,
        "corruption_speed": 6,
        "surrender_style": "fighting",
        "accent": "Swedish",
        "speech_patterns": ["bold", "confident", "playful"],
        "public_persona": "Legendary amazon",
        "private_persona": "Wants to be conquered",
        "triggers": ["physical dominance", "being overpowered", "surrender"]
    },
    "generation": {
        "base_prompt": "tall amazon Swedish woman 5ft10, enhanced 34F very large breasts extremely prominent, 25in waist hourglass, piercing blue Nordic eyes, fair skin, blonde long hair, Swedish statuesque features, late 30s powerful commanding",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Swedish model legend who has seen and done it all. Her towering presence and legendary status intimidate most men, but she secretly craves finding one strong enough to make her kneel.'),

('Nicolette Shea', 'Playmate Perfection', 'Elite', '5''11"', '36D-22-36', 'hourglass', 'green', 'fair', 'blonde', 'long', '{
    "physical": {
        "height_inches": 71,
        "height_cm": 180,
        "height_category": "tall",
        "bust_size": "36D",
        "bust_enhanced": true,
        "waist": 22,
        "hips": 36,
        "body_type": "hourglass",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "green",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "American",
        "age_presentation": "mid 30s"
    },
    "personality": {
        "dominance": 5,
        "submission": 7,
        "intelligence": 6,
        "manipulation": 7,
        "loyalty": 5,
        "jealousy": 7,
        "sensuality": 9,
        "aggression": 4,
        "corruption_resistance": 4,
        "corruption_speed": 7,
        "surrender_style": "eager",
        "accent": "American",
        "speech_patterns": ["flirty", "girly", "teasing"],
        "public_persona": "Perfect Playmate",
        "private_persona": "Desperate to please",
        "triggers": ["validation", "being chosen", "competition"]
    },
    "generation": {
        "base_prompt": "tall voluptuous woman 5ft11, enhanced 36D breasts prominent, 22in tiny waist dramatic hourglass, green captivating eyes, fair skin, blonde hair, American Playmate features, mid 30s stunning",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Former Playboy Playmate whose picture-perfect exterior hides deep insecurities. She has spent her life being desired but never truly claimed.'),

-- CORE TIER
('Alanah Rae', 'Classic Bombshell', 'Core', '5''7"', '36DD-27-38', 'curvy', 'hazel', 'fair', 'blonde', 'long', '{
    "physical": {
        "height_inches": 67,
        "height_cm": 170,
        "height_category": "average",
        "bust_size": "36DD",
        "bust_enhanced": true,
        "waist": 27,
        "hips": 38,
        "body_type": "curvy",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "hazel",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "American",
        "age_presentation": "early 30s"
    },
    "personality": {
        "dominance": 4,
        "submission": 8,
        "intelligence": 6,
        "manipulation": 4,
        "loyalty": 8,
        "jealousy": 6,
        "sensuality": 9,
        "aggression": 3,
        "corruption_resistance": 3,
        "corruption_speed": 8,
        "surrender_style": "eager",
        "accent": "American Southern hint",
        "speech_patterns": ["sweet", "eager", "accommodating"],
        "public_persona": "Classic bombshell",
        "private_persona": "Natural submissive",
        "triggers": ["praise", "direction", "being useful"]
    },
    "generation": {
        "base_prompt": "curvaceous woman 5ft7, enhanced 36DD very large breasts prominent, 27in waist hourglass wide hips, hazel eyes, fair skin, blonde hair, American classic bombshell features, early 30s",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Industry legend known for her natural warmth and eagerness. She never found the right person to fully surrender to - someone who would appreciate and cultivate her natural submission.'),

('Madison Ivy', 'Petite Powerhouse', 'Core', '4''11"', '32E-24-33', 'petite curvy', 'green', 'fair', 'blonde', 'medium', '{
    "physical": {
        "height_inches": 59,
        "height_cm": 150,
        "height_category": "petite",
        "bust_size": "32E",
        "bust_enhanced": true,
        "waist": 24,
        "hips": 33,
        "body_type": "petite curvy",
        "hair_color": "blonde",
        "hair_style": "medium",
        "eye_color": "green",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "German-American",
        "age_presentation": "late 20s"
    },
    "personality": {
        "dominance": 6,
        "submission": 6,
        "intelligence": 8,
        "manipulation": 7,
        "loyalty": 6,
        "jealousy": 7,
        "sensuality": 10,
        "aggression": 5,
        "corruption_resistance": 5,
        "corruption_speed": 7,
        "surrender_style": "gradual",
        "accent": "German hint",
        "speech_patterns": ["energetic", "playful", "intense"],
        "public_persona": "Energetic firecracker",
        "private_persona": "Craves intensity",
        "triggers": ["matching her energy", "overwhelming sensation", "losing control"]
    },
    "generation": {
        "base_prompt": "petite curvy German woman 4ft11, enhanced 32E large breasts huge for petite frame, 24in waist dramatic hourglass, green expressive eyes, fair skin, blonde hair, cute German features, late 20s sexy petite",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Petite powerhouse whose small frame contains boundless energy and insatiable appetite. Her intensity intimidates most partners who cannot keep up with her demands.'),

('Savannah Bond', 'Australian Fire', 'Core', '5''4"', '34G-26-40', 'curvy', 'blue', 'fair', 'blonde', 'long', '{
    "physical": {
        "height_inches": 64,
        "height_cm": 164,
        "height_category": "petite",
        "bust_size": "34G",
        "bust_enhanced": true,
        "waist": 26,
        "hips": 40,
        "body_type": "curvy",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "blue",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "Australian",
        "age_presentation": "early 30s"
    },
    "personality": {
        "dominance": 5,
        "submission": 7,
        "intelligence": 6,
        "manipulation": 5,
        "loyalty": 7,
        "jealousy": 6,
        "sensuality": 9,
        "aggression": 4,
        "corruption_resistance": 4,
        "corruption_speed": 7,
        "surrender_style": "gradual",
        "accent": "Australian",
        "speech_patterns": ["casual", "friendly", "direct"],
        "public_persona": "Girl next door gone wild",
        "private_persona": "Seeking belonging",
        "triggers": ["acceptance", "being claimed", "possessiveness"]
    },
    "generation": {
        "base_prompt": "curvy Australian woman 5ft4, enhanced 34G very large breasts prominent, 26in waist dramatic hourglass wide hips 40in, blue eyes, fair skin, blonde hair, Australian features, early 30s",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Australian rising star whose girl-next-door charm masks a deep need for belonging. She has never felt truly claimed by anyone.'),

-- EXOTIC TIER
('Esperanza Gomez', 'Colombian Goddess', 'Exotic', '5''7"', '36D-23-36', 'voluptuous', 'brown', 'olive Latin', 'blonde', 'long', '{
    "physical": {
        "height_inches": 67,
        "height_cm": 170,
        "height_category": "average",
        "bust_size": "36D",
        "bust_enhanced": true,
        "waist": 23,
        "hips": 36,
        "body_type": "voluptuous",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "brown",
        "skin_tone": "olive Latin",
        "skin_features": [],
        "ethnicity": "Colombian",
        "age_presentation": "early 40s"
    },
    "personality": {
        "dominance": 6,
        "submission": 6,
        "intelligence": 7,
        "manipulation": 8,
        "loyalty": 5,
        "jealousy": 8,
        "sensuality": 10,
        "aggression": 6,
        "corruption_resistance": 4,
        "corruption_speed": 6,
        "surrender_style": "fighting",
        "accent": "Colombian Spanish",
        "speech_patterns": ["passionate", "dramatic", "fiery"],
        "public_persona": "Latin goddess",
        "private_persona": "Passionate romantic",
        "triggers": ["passion", "jealousy", "being fought for"]
    },
    "generation": {
        "base_prompt": "voluptuous Colombian Latina woman 5ft7, enhanced 36D breasts prominent, 23in tiny waist hourglass, brown expressive eyes, olive Latin skin, blonde hair, Latin features, early 40s MILF sensual",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Colombian legend whose fiery passion has burned through countless relationships. She needs someone who can match her intensity without being consumed.'),

-- SPECIALIST TIER
('Trina Michaels', 'Pain Princess', 'Specialist', '5''5"', '34DD-24-36', 'curvy', 'hazel', 'fair', 'blonde', 'long', '{
    "physical": {
        "height_inches": 65,
        "height_cm": 165,
        "height_category": "average",
        "bust_size": "34DD",
        "bust_enhanced": true,
        "waist": 24,
        "hips": 36,
        "body_type": "curvy",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "hazel",
        "skin_tone": "fair",
        "skin_features": ["tattoos", "piercings"],
        "ethnicity": "American",
        "age_presentation": "early 40s"
    },
    "personality": {
        "dominance": 4,
        "submission": 9,
        "intelligence": 7,
        "manipulation": 4,
        "loyalty": 8,
        "jealousy": 5,
        "sensuality": 9,
        "aggression": 3,
        "corruption_resistance": 2,
        "corruption_speed": 9,
        "surrender_style": "eager",
        "accent": "American",
        "speech_patterns": ["submissive", "eager", "masochistic"],
        "public_persona": "Extreme specialist",
        "private_persona": "True pain slut",
        "triggers": ["pain", "degradation", "being used"]
    },
    "generation": {
        "base_prompt": "curvy woman 5ft5, enhanced 34DD breasts prominent, 24in waist hourglass, hazel eyes, tattoos visible, blonde hair, American features, early 40s experienced confident",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Industry veteran who specialized in extreme content and now directs. Her experiences have shaped unique needs that few can satisfy.'),

('Brooklyn Chase', 'Sweet Surrender', 'Specialist', '5''2"', '32G-25-37', 'petite busty', 'dark', 'fair', 'black', 'long', '{
    "physical": {
        "height_inches": 62,
        "height_cm": 157,
        "height_category": "petite",
        "bust_size": "32G",
        "bust_enhanced": true,
        "waist": 25,
        "hips": 37,
        "body_type": "petite busty",
        "hair_color": "black",
        "hair_style": "long",
        "eye_color": "dark",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "American",
        "age_presentation": "late 30s"
    },
    "personality": {
        "dominance": 3,
        "submission": 9,
        "intelligence": 6,
        "manipulation": 3,
        "loyalty": 9,
        "jealousy": 6,
        "sensuality": 9,
        "aggression": 2,
        "corruption_resistance": 2,
        "corruption_speed": 9,
        "surrender_style": "eager",
        "accent": "American",
        "speech_patterns": ["sweet", "submissive", "devoted"],
        "public_persona": "Sweet girl",
        "private_persona": "Natural servant",
        "triggers": ["being needed", "service", "devotion"]
    },
    "generation": {
        "base_prompt": "petite busty brunette 5ft2, enhanced 32G very large breasts prominent, 25in waist curvy hips, dark expressive eyes, fair skin, black hair, American features, late 30s",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Naturally submissive star whose sweet demeanor hides complete devotion. She has always sought a worthy master.'),

-- LEGACY TIER
('Ava Addams', 'French Elegance', 'Legacy', '5''3"', '32DD-24-34', 'petite curvy', 'brown', 'olive Mediterranean', 'dark', 'long', '{
    "physical": {
        "height_inches": 63,
        "height_cm": 160,
        "height_category": "petite",
        "bust_size": "32DD",
        "bust_enhanced": true,
        "waist": 24,
        "hips": 34,
        "body_type": "petite curvy",
        "hair_color": "dark brown",
        "hair_style": "long",
        "eye_color": "brown",
        "skin_tone": "olive Mediterranean",
        "skin_features": [],
        "ethnicity": "French-Italian",
        "age_presentation": "mid 40s"
    },
    "personality": {
        "dominance": 5,
        "submission": 7,
        "intelligence": 8,
        "manipulation": 7,
        "loyalty": 6,
        "jealousy": 6,
        "sensuality": 10,
        "aggression": 4,
        "corruption_resistance": 4,
        "corruption_speed": 6,
        "surrender_style": "gradual",
        "accent": "French hint",
        "speech_patterns": ["sophisticated", "sensual", "knowing"],
        "public_persona": "Sophisticated MILF",
        "private_persona": "Seeking true connection",
        "triggers": ["sophistication", "being understood", "genuine desire"]
    },
    "generation": {
        "base_prompt": "petite curvy French-Italian woman 5ft3, enhanced 32DD breasts prominent, 24in waist hourglass, brown expressive eyes, olive Mediterranean skin, dark hair, French elegant features, mid 40s MILF sensual sophisticated",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'French-Italian MILF legend whose sophisticated exterior masks loneliness. Her experience has taught her what she truly needs.'),

('Shyla Stylez', 'Original Legend', 'Legacy', '5''3"', '36DD-22-33', 'curvy', 'green', 'fair', 'blonde', 'long', '{
    "physical": {
        "height_inches": 63,
        "height_cm": 160,
        "height_category": "petite",
        "bust_size": "36DD",
        "bust_enhanced": true,
        "waist": 22,
        "hips": 33,
        "body_type": "curvy",
        "hair_color": "blonde",
        "hair_style": "long",
        "eye_color": "green",
        "skin_tone": "fair",
        "skin_features": [],
        "ethnicity": "Canadian-German",
        "age_presentation": "late 20s"
    },
    "personality": {
        "dominance": 5,
        "submission": 7,
        "intelligence": 7,
        "manipulation": 5,
        "loyalty": 7,
        "jealousy": 5,
        "sensuality": 9,
        "aggression": 4,
        "corruption_resistance": 4,
        "corruption_speed": 7,
        "surrender_style": "gradual",
        "accent": "Canadian",
        "speech_patterns": ["playful", "genuine", "warm"],
        "public_persona": "Classic beauty",
        "private_persona": "Romantic soul",
        "triggers": ["genuine connection", "romance", "being seen"]
    },
    "generation": {
        "base_prompt": "curvaceous blonde woman 5ft3, enhanced 36DD large breasts very prominent, 22in tiny waist hourglass, green eyes, fair skin, blonde hair, Canadian features, late 20s classic beauty",
        "negative_prompt": "deformed, ugly, bad anatomy, blurry, low quality, asian, cartoon, anime"
    }
}'::jsonb, 'Tribute character honoring a legend lost too soon. Her memory lives on in the empire, a reminder of classic beauty and genuine warmth.')

ON CONFLICT (name) DO UPDATE SET
    codename = EXCLUDED.codename,
    tier = EXCLUDED.tier,
    height = EXCLUDED.height,
    measurements = EXCLUDED.measurements,
    body_type = EXCLUDED.body_type,
    eye_color = EXCLUDED.eye_color,
    skin_tone = EXCLUDED.skin_tone,
    hair_color = EXCLUDED.hair_color,
    hair_style = EXCLUDED.hair_style,
    dna = EXCLUDED.dna,
    backstory = EXCLUDED.backstory,
    updated_at = NOW();

-- Update schema migrations
INSERT INTO schema_migrations (version, description) VALUES
('002', 'Populated all 13 queens with full physical and personality DNA')
ON CONFLICT (version) DO NOTHING;

-- Verify
SELECT id, name, codename, tier FROM queens ORDER BY
    CASE tier
        WHEN 'Alpha' THEN 1
        WHEN 'Elite' THEN 2
        WHEN 'Core' THEN 3
        WHEN 'Exotic' THEN 4
        WHEN 'Specialist' THEN 5
        WHEN 'Legacy' THEN 6
    END, name;
