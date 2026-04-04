-- Add starred field to papers table
ALTER TABLE "papers" ADD COLUMN "starred" BOOLEAN NOT NULL DEFAULT false;

-- Create projects table
CREATE TABLE "projects" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "color" TEXT NOT NULL DEFAULT '#3B82F6',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projects_pkey" PRIMARY KEY ("id")
);

-- Add project_id to papers table
ALTER TABLE "papers" ADD COLUMN "project_id" TEXT;

-- Create annotations table
CREATE TABLE "annotations" (
    "id" TEXT NOT NULL,
    "paper_id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "page_number" INTEGER NOT NULL,
    "position" JSONB NOT NULL,
    "content" TEXT,
    "color" TEXT NOT NULL DEFAULT '#FFEB3B',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "annotations_pkey" PRIMARY KEY ("id")
);

-- Create reading_progress table
CREATE TABLE "reading_progress" (
    "id" TEXT NOT NULL,
    "paper_id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "current_page" INTEGER NOT NULL DEFAULT 1,
    "total_pages" INTEGER,
    "last_read_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "reading_progress_pkey" PRIMARY KEY ("id")
);

-- Create indexes for starred field
CREATE INDEX "papers_starred_idx" ON "papers"("starred");
CREATE INDEX "papers_user_id_starred_idx" ON "papers"("user_id", "starred");

-- Create indexes for projects
CREATE INDEX "projects_user_id_idx" ON "projects"("user_id");

-- Create indexes for annotations
CREATE INDEX "annotations_paper_id_idx" ON "annotations"("paper_id");
CREATE INDEX "annotations_user_id_idx" ON "annotations"("user_id");
CREATE INDEX "annotations_paper_id_page_number_idx" ON "annotations"("paper_id", "page_number");

-- Create indexes for reading_progress
CREATE INDEX "reading_progress_user_id_idx" ON "reading_progress"("user_id");
CREATE INDEX "reading_progress_last_read_at_idx" ON "reading_progress"("last_read_at");

-- Create unique constraint for reading_progress
CREATE UNIQUE INDEX "reading_progress_paper_id_user_id_key" ON "reading_progress"("paper_id", "user_id");

-- Add foreign key constraints
ALTER TABLE "papers" ADD CONSTRAINT "papers_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "projects" ADD CONSTRAINT "projects_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "annotations" ADD CONSTRAINT "annotations_paper_id_fkey" FOREIGN KEY ("paper_id") REFERENCES "papers"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "annotations" ADD CONSTRAINT "annotations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "reading_progress" ADD CONSTRAINT "reading_progress_paper_id_fkey" FOREIGN KEY ("paper_id") REFERENCES "papers"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "reading_progress" ADD CONSTRAINT "reading_progress_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;