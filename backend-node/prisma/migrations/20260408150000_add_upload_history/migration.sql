-- CreateTable
CREATE TABLE "upload_history" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "paper_id" TEXT,
    "filename" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'PROCESSING',
    "chunks_count" INTEGER,
    "llm_tokens" INTEGER,
    "page_count" INTEGER,
    "image_count" INTEGER,
    "table_count" INTEGER,
    "error_message" TEXT,
    "processing_time" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "upload_history_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "upload_history_user_id_created_at_idx" ON "upload_history"("user_id", "created_at" DESC);

-- AddForeignKey
ALTER TABLE "upload_history" ADD CONSTRAINT "upload_history_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "upload_history" ADD CONSTRAINT "upload_history_paper_id_fkey" FOREIGN KEY ("paper_id") REFERENCES "papers"("id") ON DELETE SET NULL ON UPDATE CASCADE;