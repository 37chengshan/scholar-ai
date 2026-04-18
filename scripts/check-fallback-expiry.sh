#!/usr/bin/env bash
set -euo pipefail

register_file="docs/governance/fallback-register.yaml"

if [[ ! -f "$register_file" ]]; then
  echo "[fallback-expiry] missing required file: $register_file" >&2
  exit 1
fi

if ! command -v ruby >/dev/null 2>&1; then
  echo "[fallback-expiry] ruby is required" >&2
  exit 1
fi

ruby -e '
require "yaml"
require "date"

file = ARGV[0]
allowed_status = %w[active retired removed]
required_keys = %w[id owner component introduced_at expires_at removal_plan status tracking_ref]

begin
  data = YAML.safe_load(File.read(file), aliases: false)
rescue StandardError => e
  warn "[fallback-expiry] invalid YAML in #{file}: #{e.message}"
  exit 1
end

unless data.is_a?(Hash) && data["records"].is_a?(Array)
  warn "[fallback-expiry] #{file} must include records array"
  exit 1
end

records = data["records"]
owners = Array(data["owners"]).map(&:to_s)
seen = {}
fail_count = 0
expired_active_count = 0
active_count = 0

records.each do |record|
  unless record.is_a?(Hash)
    warn "[fallback-expiry] each record must be mapping"
    fail_count += 1
    next
  end

  missing = required_keys.reject { |k| record.key?(k) }
  unless missing.empty?
    warn "[fallback-expiry] missing keys in record: #{missing.join(", ")}"
    fail_count += 1
    next
  end

  id = record["id"].to_s.strip
  owner = record["owner"].to_s.strip
  status = record["status"].to_s.strip

  if id.empty?
    warn "[fallback-expiry] empty id"
    fail_count += 1
  elsif seen[id]
    warn "[fallback-expiry] duplicated id: #{id}"
    fail_count += 1
  else
    seen[id] = true
  end

  unless owners.include?(owner)
    warn "[fallback-expiry] owner not in owners list: #{owner}"
    fail_count += 1
  end

  unless allowed_status.include?(status)
    warn "[fallback-expiry] invalid status for #{id}: #{status}"
    fail_count += 1
    next
  end

  begin
    introduced_at = Date.iso8601(record["introduced_at"].to_s)
    expires_at = Date.iso8601(record["expires_at"].to_s)
  rescue ArgumentError
    warn "[fallback-expiry] invalid date in #{id}"
    fail_count += 1
    next
  end

  if expires_at < introduced_at
    warn "[fallback-expiry] expires_at earlier than introduced_at for #{id}"
    fail_count += 1
  end

  removal_plan = record["removal_plan"].to_s.strip
  tracking_ref = record["tracking_ref"].to_s.strip

  if removal_plan.empty? || removal_plan == "-"
    warn "[fallback-expiry] removal_plan is required for #{id}"
    fail_count += 1
  end

  if tracking_ref.empty? || tracking_ref == "-"
    warn "[fallback-expiry] tracking_ref is required for #{id}"
    fail_count += 1
  end

  if status == "active"
    active_count += 1
    if expires_at < Date.today
      expired_active_count += 1
      warn "[fallback-expiry] expired active fallback: #{id}, expires_at=#{expires_at}"
      fail_count += 1
    end
  end
end

puts "[fallback-expiry] active=#{active_count}, records=#{records.size}, expired_active=#{expired_active_count}"

if fail_count > 0
  warn "[fallback-expiry] failed with #{fail_count} issue(s)"
  exit 1
end

puts "[fallback-expiry] passed"
' "$register_file"
