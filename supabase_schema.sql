CREATE TABLE IF NOT EXISTS public.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    email_lower TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    username_lower TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.saved_outfits (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT,
    skin_tone TEXT NOT NULL,
    undertone TEXT NOT NULL,
    style TEXT NOT NULL,
    occasion TEXT NOT NULL,
    shirt_color TEXT NOT NULL,
    pants_color TEXT NOT NULL,
    shoes_color TEXT NOT NULL,
    score INTEGER NOT NULL,
    explanation TEXT,
    source TEXT NOT NULL DEFAULT 'streamlit',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_outfits_user_created_at
ON public.saved_outfits(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.outfit_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT,
    outfit_key TEXT NOT NULL,
    skin_tone TEXT NOT NULL,
    undertone TEXT NOT NULL,
    style TEXT NOT NULL,
    occasion TEXT NOT NULL,
    shirt_color TEXT NOT NULL,
    pants_color TEXT NOT NULL,
    shoes_color TEXT NOT NULL,
    outfit_score INTEGER NOT NULL,
    feedback TEXT NOT NULL CHECK (feedback IN ('like', 'unlike')),
    points INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'streamlit',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, outfit_key)
);

CREATE INDEX IF NOT EXISTS idx_outfit_feedback_user_updated_at
ON public.outfit_feedback(user_id, updated_at DESC);
