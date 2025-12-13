-- =============================================================================
-- Empire of Broken Queens - Generation Pipeline Schema
-- Migration: 001_generation_pipeline.sql
-- Description: Adds asset generation tracking tables alongside existing game tables
-- =============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- GENERATION_TASKS - Track all generation jobs
-- =============================================================================
CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Task identification
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN (
        'portrait', 'expression', 'pose', 'explicit', 'background',
        'video_idle', 'video_reaction', 'video_cinematic',
        'voice_line', 'dialogue_batch', 'lora_training'
    )),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN (
        'critical', 'high', 'normal', 'low', 'idle'
    )),

    -- Target (references existing queens table by name/id)
    queen_id INTEGER REFERENCES queens(id) ON DELETE CASCADE,
    queen_slug VARCHAR(100),  -- Denormalized for quick access

    -- Configuration (full config stored as JSONB)
    config JSONB NOT NULL DEFAULT '{}',

    -- Execution
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN (
        'queued', 'assigned', 'running', 'quality_check',
        'completed', 'failed', 'cancelled'
    )),
    assigned_node VARCHAR(100),
    assigned_gpu VARCHAR(50),

    -- Progress tracking
    total_count INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,

    -- Timing
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Error handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,

    -- Kubernetes integration
    k8s_job_name VARCHAR(253),
    k8s_namespace VARCHAR(63) DEFAULT 'ai-workloads',

    -- Metadata
    created_by VARCHAR(100) DEFAULT 'system',
    correlation_id UUID,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for generation_tasks
CREATE INDEX IF NOT EXISTS idx_gen_tasks_queen ON generation_tasks(queen_id);
CREATE INDEX IF NOT EXISTS idx_gen_tasks_queen_slug ON generation_tasks(queen_slug);
CREATE INDEX IF NOT EXISTS idx_gen_tasks_status ON generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_gen_tasks_type ON generation_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_gen_tasks_priority ON generation_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_gen_tasks_queued ON generation_tasks(queued_at) WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS idx_gen_tasks_correlation ON generation_tasks(correlation_id);

-- =============================================================================
-- GENERATED_ASSETS - Track all generated files
-- =============================================================================
CREATE TABLE IF NOT EXISTS generated_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Relationships
    task_id UUID REFERENCES generation_tasks(id) ON DELETE SET NULL,
    queen_id INTEGER REFERENCES queens(id) ON DELETE CASCADE,
    queen_slug VARCHAR(100),

    -- Asset identification
    asset_type VARCHAR(50) NOT NULL CHECK (asset_type IN (
        'portrait', 'expression', 'pose', 'explicit', 'background',
        'video_idle', 'video_reaction', 'video_cinematic',
        'voice_line', 'lora_model', 'voice_model'
    )),
    file_path VARCHAR(1000) NOT NULL,
    file_name VARCHAR(255),
    file_size BIGINT,
    file_hash VARCHAR(64),  -- SHA256
    mime_type VARCHAR(100),

    -- Image dimensions (for images/videos)
    width INTEGER,
    height INTEGER,
    duration_seconds DECIMAL(10,2),  -- For audio/video

    -- Quality scores (0.0 - 1.0)
    aesthetic_score DECIMAL(5,4),
    technical_score DECIMAL(5,4),
    face_match_score DECIMAL(5,4),
    composite_score DECIMAL(5,4),

    -- Approval
    approved BOOLEAN DEFAULT FALSE,
    approval_method VARCHAR(50) CHECK (approval_method IN ('auto', 'manual', 'threshold')),
    rejection_reason VARCHAR(500),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(100),

    -- Generation metadata
    generation_params JSONB DEFAULT '{}',
    prompt_used TEXT,
    negative_prompt TEXT,
    seed BIGINT,
    model_used VARCHAR(200),
    lora_used VARCHAR(200),
    lora_strength DECIMAL(3,2),

    -- Embedding reference (for similarity search in Qdrant)
    embedding_id VARCHAR(100),
    embedding_collection VARCHAR(100),

    -- Tags for organization
    tags TEXT[] DEFAULT '{}',

    -- Timestamps
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for generated_assets
CREATE INDEX IF NOT EXISTS idx_assets_queen ON generated_assets(queen_id);
CREATE INDEX IF NOT EXISTS idx_assets_queen_slug ON generated_assets(queen_slug);
CREATE INDEX IF NOT EXISTS idx_assets_task ON generated_assets(task_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON generated_assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_approved ON generated_assets(approved);
CREATE INDEX IF NOT EXISTS idx_assets_composite_score ON generated_assets(composite_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_assets_generated_at ON generated_assets(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_tags ON generated_assets USING GIN(tags);

-- =============================================================================
-- QUALITY_METRICS - Aggregated quality statistics
-- =============================================================================
CREATE TABLE IF NOT EXISTS quality_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    granularity VARCHAR(20) NOT NULL CHECK (granularity IN ('hourly', 'daily', 'weekly', 'monthly')),

    -- Target (null for global metrics)
    queen_id INTEGER REFERENCES queens(id) ON DELETE CASCADE,
    queen_slug VARCHAR(100),
    task_type VARCHAR(50),

    -- Counts
    total_generated INTEGER DEFAULT 0,
    total_approved INTEGER DEFAULT 0,
    total_rejected INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,4),

    -- Score distributions (min, max, mean, stddev, percentiles)
    aesthetic_scores JSONB DEFAULT '{}',
    technical_scores JSONB DEFAULT '{}',
    face_match_scores JSONB DEFAULT '{}',
    composite_scores JSONB DEFAULT '{}',

    -- Rejection reasons breakdown
    rejection_breakdown JSONB DEFAULT '{}',

    -- Performance metrics
    avg_generation_time_seconds DECIMAL(10,2),
    total_gpu_hours DECIMAL(10,4),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for quality_metrics
CREATE INDEX IF NOT EXISTS idx_quality_period ON quality_metrics(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_quality_queen ON quality_metrics(queen_id);
CREATE INDEX IF NOT EXISTS idx_quality_granularity ON quality_metrics(granularity);

-- =============================================================================
-- LORA_MODELS - Track trained LoRA models
-- =============================================================================
CREATE TABLE IF NOT EXISTS lora_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identity
    queen_id INTEGER REFERENCES queens(id) ON DELETE CASCADE,
    queen_slug VARCHAR(100),
    model_name VARCHAR(200) NOT NULL,
    version INTEGER DEFAULT 1,

    -- Model details
    base_model VARCHAR(200) NOT NULL,
    network_type VARCHAR(50) DEFAULT 'lora',  -- lora, locon, loha
    network_dim INTEGER,
    network_alpha INTEGER,

    -- Training configuration
    training_config JSONB DEFAULT '{}',
    training_images INTEGER,
    training_steps INTEGER,
    epochs INTEGER,
    learning_rate DECIMAL(10,8),
    final_loss DECIMAL(10,6),

    -- Files
    model_path VARCHAR(1000) NOT NULL,
    model_size BIGINT,

    -- Status
    status VARCHAR(50) DEFAULT 'training' CHECK (status IN (
        'queued', 'training', 'completed', 'failed', 'active', 'archived'
    )),
    is_active BOOLEAN DEFAULT FALSE,  -- Currently used for generation

    -- Quality metrics from test generations
    test_scores JSONB DEFAULT '{}',
    test_images_path VARCHAR(1000),

    -- Training job reference
    training_task_id UUID REFERENCES generation_tasks(id),

    -- Timestamps
    training_started_at TIMESTAMP WITH TIME ZONE,
    training_completed_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for lora_models
CREATE INDEX IF NOT EXISTS idx_lora_queen ON lora_models(queen_id);
CREATE INDEX IF NOT EXISTS idx_lora_queen_slug ON lora_models(queen_slug);
CREATE INDEX IF NOT EXISTS idx_lora_status ON lora_models(status);
CREATE INDEX IF NOT EXISTS idx_lora_active ON lora_models(is_active) WHERE is_active = TRUE;

-- Unique constraint: only one active LoRA per queen
CREATE UNIQUE INDEX IF NOT EXISTS idx_lora_unique_active
    ON lora_models(queen_id) WHERE is_active = TRUE;

-- =============================================================================
-- VOICE_MODELS - Track voice clone models
-- =============================================================================
CREATE TABLE IF NOT EXISTS voice_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    queen_id INTEGER REFERENCES queens(id) ON DELETE CASCADE,
    queen_slug VARCHAR(100),
    model_name VARCHAR(200) NOT NULL,
    version INTEGER DEFAULT 1,

    -- Model type
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN (
        'gpt-sovits', 'xtts', 'rvc', 'bark', 'tortoise'
    )),

    -- Training data
    reference_clips JSONB DEFAULT '[]',  -- Array of {path, duration, text}
    total_duration_seconds DECIMAL(10,2),

    -- Files
    model_path VARCHAR(1000) NOT NULL,
    model_size BIGINT,

    -- Status
    status VARCHAR(50) DEFAULT 'training' CHECK (status IN (
        'queued', 'training', 'completed', 'failed', 'active', 'archived'
    )),
    is_active BOOLEAN DEFAULT FALSE,

    -- Quality metrics
    similarity_score DECIMAL(5,4),
    naturalness_score DECIMAL(5,4),
    test_samples JSONB DEFAULT '[]',

    -- Training job reference
    training_task_id UUID REFERENCES generation_tasks(id),

    -- Timestamps
    training_started_at TIMESTAMP WITH TIME ZONE,
    training_completed_at TIMESTAMP WITH TIME ZONE,
    activated_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for voice_models
CREATE INDEX IF NOT EXISTS idx_voice_queen ON voice_models(queen_id);
CREATE INDEX IF NOT EXISTS idx_voice_queen_slug ON voice_models(queen_slug);
CREATE INDEX IF NOT EXISTS idx_voice_status ON voice_models(status);
CREATE INDEX IF NOT EXISTS idx_voice_active ON voice_models(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- GENERATION_QUEUE - Priority queue view for scheduler
-- =============================================================================
CREATE OR REPLACE VIEW generation_queue AS
SELECT
    gt.id,
    gt.task_type,
    gt.priority,
    gt.queen_id,
    gt.queen_slug,
    gt.config,
    gt.status,
    gt.queued_at,
    gt.retry_count,
    q.name as queen_name,
    q.tier as queen_tier,
    CASE gt.priority
        WHEN 'critical' THEN 1000000
        WHEN 'high' THEN 100000
        WHEN 'normal' THEN 10000
        WHEN 'low' THEN 1000
        WHEN 'idle' THEN 100
    END as priority_score,
    -- Time in queue bonus (older = higher priority within same level)
    EXTRACT(EPOCH FROM (NOW() - gt.queued_at)) as queue_age_seconds
FROM generation_tasks gt
LEFT JOIN queens q ON gt.queen_id = q.id
WHERE gt.status = 'queued'
ORDER BY
    CASE gt.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'normal' THEN 3
        WHEN 'low' THEN 4
        WHEN 'idle' THEN 5
    END,
    gt.queued_at ASC;

-- =============================================================================
-- QUEEN_ASSET_SUMMARY - Dashboard view for queen assets
-- =============================================================================
CREATE OR REPLACE VIEW queen_asset_summary AS
SELECT
    q.id as queen_id,
    q.name as queen_name,
    LOWER(REPLACE(q.name, ' ', '-')) as queen_slug,
    q.tier,
    q.portrait_count,
    q.lora_path,

    -- Asset counts by type
    COUNT(ga.id) FILTER (WHERE ga.asset_type = 'portrait' AND ga.approved) as approved_portraits,
    COUNT(ga.id) FILTER (WHERE ga.asset_type = 'expression' AND ga.approved) as approved_expressions,
    COUNT(ga.id) FILTER (WHERE ga.asset_type = 'pose' AND ga.approved) as approved_poses,
    COUNT(ga.id) FILTER (WHERE ga.asset_type = 'explicit' AND ga.approved) as approved_explicit,
    COUNT(ga.id) FILTER (WHERE ga.asset_type = 'voice_line' AND ga.approved) as approved_voice_lines,

    -- Pending assets
    COUNT(ga.id) FILTER (WHERE NOT ga.approved AND ga.rejection_reason IS NULL) as pending_review,

    -- Quality averages
    AVG(ga.composite_score) FILTER (WHERE ga.approved) as avg_quality_score,

    -- Latest generation
    MAX(ga.generated_at) as last_generated_at,

    -- Active models
    (SELECT model_path FROM lora_models lm WHERE lm.queen_id = q.id AND lm.is_active LIMIT 1) as active_lora,
    (SELECT model_path FROM voice_models vm WHERE vm.queen_id = q.id AND vm.is_active LIMIT 1) as active_voice_model

FROM queens q
LEFT JOIN generated_assets ga ON ga.queen_id = q.id
GROUP BY q.id, q.name, q.tier, q.portrait_count, q.lora_path;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_generation_tasks_updated_at ON generation_tasks;
CREATE TRIGGER update_generation_tasks_updated_at
    BEFORE UPDATE ON generation_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lora_models_updated_at ON lora_models;
CREATE TRIGGER update_lora_models_updated_at
    BEFORE UPDATE ON lora_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_voice_models_updated_at ON voice_models;
CREATE TRIGGER update_voice_models_updated_at
    BEFORE UPDATE ON voice_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate composite score
CREATE OR REPLACE FUNCTION calculate_composite_score(
    aesthetic DECIMAL,
    technical DECIMAL,
    face_match DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    -- Weighted average: aesthetic 40%, technical 30%, face_match 30%
    RETURN (COALESCE(aesthetic, 0) * 0.4 +
            COALESCE(technical, 0) * 0.3 +
            COALESCE(face_match, 0) * 0.3);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get next task from queue
CREATE OR REPLACE FUNCTION get_next_generation_task(
    p_node VARCHAR DEFAULT NULL,
    p_task_types VARCHAR[] DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
BEGIN
    SELECT id INTO v_task_id
    FROM generation_tasks
    WHERE status = 'queued'
      AND (p_task_types IS NULL OR task_type = ANY(p_task_types))
    ORDER BY
        CASE priority
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'normal' THEN 3
            WHEN 'low' THEN 4
            WHEN 'idle' THEN 5
        END,
        queued_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF v_task_id IS NOT NULL THEN
        UPDATE generation_tasks
        SET status = 'assigned',
            assigned_node = p_node,
            started_at = NOW()
        WHERE id = v_task_id;
    END IF;

    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA - Quality thresholds configuration
-- =============================================================================
CREATE TABLE IF NOT EXISTS generation_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO generation_config (key, value, description) VALUES
('quality_thresholds', '{
    "aesthetic_min": 0.6,
    "technical_min": 0.7,
    "face_match_min": 0.75,
    "composite_min": 0.65,
    "auto_approve_threshold": 0.8
}', 'Minimum quality scores for approval')
ON CONFLICT (key) DO NOTHING;

INSERT INTO generation_config (key, value, description) VALUES
('default_generation_params', '{
    "portrait": {
        "width": 1024,
        "height": 1024,
        "steps": 30,
        "cfg": 7.0,
        "sampler": "dpmpp_2m_sde_gpu"
    },
    "expression": {
        "width": 768,
        "height": 768,
        "steps": 25,
        "cfg": 7.0
    },
    "pose": {
        "width": 768,
        "height": 1152,
        "steps": 30,
        "cfg": 7.0
    }
}', 'Default parameters per generation type')
ON CONFLICT (key) DO NOTHING;

INSERT INTO generation_config (key, value, description) VALUES
('overnight_pipeline', '{
    "enabled": true,
    "start_hour": 22,
    "end_hour": 6,
    "max_concurrent": 2,
    "priority_override": "normal",
    "generate_report": true
}', 'Overnight generation pipeline settings')
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================
GRANT ALL ON ALL TABLES IN SCHEMA public TO hydra;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO hydra;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO hydra;

-- =============================================================================
-- MIGRATION TRACKING
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO schema_migrations (version, description) VALUES
('001', 'Generation pipeline tables: generation_tasks, generated_assets, quality_metrics, lora_models, voice_models')
ON CONFLICT (version) DO NOTHING;

-- =============================================================================
-- Done!
-- =============================================================================
