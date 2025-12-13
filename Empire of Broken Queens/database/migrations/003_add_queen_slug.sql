-- Migration: Add slug column to queens table
-- Date: December 12, 2025
-- Purpose: Enable easy lookup by slug instead of computed from name

-- Add slug column if not exists
ALTER TABLE queens ADD COLUMN IF NOT EXISTS slug VARCHAR(50);

-- Populate slugs from first name (lowercase)
UPDATE queens SET slug = LOWER(REPLACE(SPLIT_PART(name, ' ', 1), '''', ''))
WHERE slug IS NULL;

-- Make slug required
ALTER TABLE queens ALTER COLUMN slug SET NOT NULL;

-- Create unique index for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_queens_slug ON queens(slug);

-- Verify migration
SELECT id, name, slug FROM queens ORDER BY id;
