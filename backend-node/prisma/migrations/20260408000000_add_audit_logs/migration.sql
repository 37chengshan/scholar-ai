-- Create audit_logs table for tool execution audit trail
-- Per D-08, D-09: Track all tool executions with performance metrics, 30-day retention

CREATE TABLE "audit_logs" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "tool" TEXT NOT NULL,
    "risk_level" TEXT NOT NULL,
    "params" JSONB,
    "result" TEXT,
    "tokens_used" INTEGER,
    "cost_cny" DOUBLE PRECISION,
    "execution_ms" INTEGER,
    "ip_address" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- Add foreign key constraint to users
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_user_id_fkey" 
    FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Create indexes for query performance
CREATE INDEX "audit_logs_user_id_idx" ON "audit_logs"("user_id");
CREATE INDEX "audit_logs_created_at_idx" ON "audit_logs"("created_at");
CREATE INDEX "audit_logs_risk_level_idx" ON "audit_logs"("risk_level");