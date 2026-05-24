CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    current_inferred_skin_tone TEXT,
    current_inferred_undertone TEXT,
    skin_profile_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    skin_analysis_count INTEGER NOT NULL DEFAULT 0,
    historical_skin_tone_estimates JSONB NOT NULL DEFAULT '[]'::jsonb,
    historical_undertone_estimates JSONB NOT NULL DEFAULT '[]'::jsonb,
    preferred_color_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    disliked_color_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    slot_color_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    preferred_style_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    preferred_occasion_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
    interaction_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_signals JSONB NOT NULL DEFAULT '{}'::jsonb,
    insights JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    action TEXT NOT NULL,
    profile JSONB NOT NULL,
    outfit JSONB NOT NULL,
    source TEXT NOT NULL,
    original_outfit JSONB,
    refined_outfit JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS skin_analysis_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    skin_tone TEXT NOT NULL,
    undertone TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    confidence_label TEXT,
    brightness DOUBLE PRECISION,
    dominant_skin_hex TEXT,
    sample_pixel_count INTEGER,
    quality_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    note TEXT,
    analyzed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_looks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    profile JSONB NOT NULL,
    outfit JSONB NOT NULL,
    source TEXT NOT NULL,
    explanation TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    saved_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_created_at ON user_feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_action ON user_feedback(user_id, action);
CREATE INDEX IF NOT EXISTS idx_skin_analysis_history_user_analyzed_at ON skin_analysis_history(user_id, analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_looks_user_saved_at ON saved_looks(user_id, saved_at DESC);
