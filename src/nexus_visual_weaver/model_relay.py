"""Quota-aware helper model rotation for NEXUS Visual Weaver.

The relay mirrors the useful GMR/ModelRelay ideas from NEXUS without copying
the source: pinned creative anchors stay fixed, helper lanes can rotate, and
all decisions carry a compact context packet for fallback continuity.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


PINNED_LANES = {"image_generation", "grounding", "security"}
ROTATABLE_LANES = {
    "prompt_router",
    "taste_judge",
    "audio_lore_tts",
    "video_repair",
    "hf_catalog_research",
    "modal_job_runner",
}
PUBLIC_SAFE_LICENSES = {"apache-2.0", "mit", "bsd-3-clause", "gemma", "public_safe", "openrail"}
PRIVATE_LICENSES = {"private_research", "research_noncommercial", "commercial_required", "other", "unknown", "review_required"}
STRATEGY_ALIASES = {
    "speed": "latency_first",
    "fast": "latency_first",
    "safe_public": "license_safe_public",
    "public": "license_safe_public",
    "private": "private_research",
}
DEFAULT_ROTATION_BUDGET_B = 5.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


@dataclass
class ContextPacket:
    lane: str
    task: str
    public_demo: bool
    budget_b: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRecord:
    model_id: str
    lane: str
    provider: str
    repo_id: str
    license_gate: str
    params_b: float
    cost_hint: str
    rpm_limit: int
    rpd_limit: int
    cooldown_until: datetime | None = None
    health: str = "healthy"
    latency_ms: int = 500
    quality_score: float = 0.75
    fallback_chain: tuple[str, ...] = ()
    pinned: bool = False
    adult_capable: bool = False
    last_failure: str | None = None
    success_count: int = 0
    failure_count: int = 0
    minute_calls: list[datetime] = field(default_factory=list)
    day_calls: list[datetime] = field(default_factory=list)

    @property
    def public_safe(self) -> bool:
        return self.license_gate in PUBLIC_SAFE_LICENSES and not self.adult_capable

    def in_cooldown(self, now: datetime | None = None) -> bool:
        now = now or utc_now()
        return bool(self.cooldown_until and self.cooldown_until > now)

    def to_dict(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or utc_now()
        return {
            "model_id": self.model_id,
            "lane": self.lane,
            "provider": self.provider,
            "repo_id": self.repo_id,
            "license_gate": self.license_gate,
            "params_b": self.params_b,
            "cost_hint": self.cost_hint,
            "rpm_limit": self.rpm_limit,
            "rpd_limit": self.rpd_limit,
            "cooldown_until": _iso(self.cooldown_until),
            "in_cooldown": self.in_cooldown(now),
            "health": self.health,
            "latency_ms": self.latency_ms,
            "quality_score": self.quality_score,
            "fallback_chain": list(self.fallback_chain),
            "pinned": self.pinned,
            "adult_capable": self.adult_capable,
            "last_failure": self.last_failure,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "rpm_used": len(self.minute_calls),
            "rpd_used": len(self.day_calls),
        }


@dataclass
class LaneDecision:
    lane: str
    strategy: str
    primary: ModelRecord | None
    fallbacks: list[ModelRecord]
    reason: str
    expected_cost_hint: str
    quota_impact: dict[str, Any]
    context_packet: ContextPacket
    skipped: list[str] = field(default_factory=list)

    @property
    def pinned(self) -> bool:
        return bool(self.primary and self.primary.pinned)

    @property
    def rotatable(self) -> bool:
        return self.lane in ROTATABLE_LANES

    def to_dict(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or utc_now()
        return {
            "lane": self.lane,
            "strategy": self.strategy,
            "primary": self.primary.to_dict(now) if self.primary else None,
            "fallbacks": [record.to_dict(now) for record in self.fallbacks],
            "reason": self.reason,
            "expected_cost_hint": self.expected_cost_hint,
            "quota_impact": self.quota_impact,
            "context_packet": self.context_packet.to_dict(),
            "skipped": self.skipped,
            "pinned": self.pinned,
            "rotatable": self.rotatable,
        }


@dataclass
class _DedupEntry:
    value: Any
    expires_at: datetime


class WeaverModelRelay:
    """Selects helper models while preserving pinned creative anchors."""

    def __init__(
        self,
        records: list[ModelRecord] | None = None,
        now_fn: Callable[[], datetime] = utc_now,
    ) -> None:
        self._now_fn = now_fn
        self.records: dict[str, ModelRecord] = {record.model_id: record for record in (records or default_model_records())}
        self._dedup: dict[str, _DedupEntry] = {}
        self._dedup_hits = 0

    def select_lane(
        self,
        lane: str,
        task: str = "",
        budget: float | None = None,
        public_demo: bool = True,
        strategy: str = "quality_first",
    ) -> LaneDecision:
        lane = self.normalize_lane(lane)
        strategy = self.normalize_strategy(strategy)
        budget_b = float(budget if budget is not None else (32.0 if lane in PINNED_LANES else DEFAULT_ROTATION_BUDGET_B))
        now = self._now()
        context = ContextPacket(lane=lane, task=task or lane, public_demo=public_demo, budget_b=budget_b)

        lane_records = [record for record in self.records.values() if record.lane == lane]
        if lane in PINNED_LANES:
            primary = next((record for record in lane_records if record.pinned), None)
            return LaneDecision(
                lane=lane,
                strategy="pinned",
                primary=primary,
                fallbacks=[],
                reason="Pinned core lane; rotation disabled for creative identity, grounding, or security.",
                expected_cost_hint=primary.cost_hint if primary else "unavailable",
                quota_impact=self._quota_impact(primary, now) if primary else {},
                context_packet=context,
                skipped=[] if primary else [f"{lane}: no pinned model registered"],
            )

        candidates, skipped = self._eligible_records(lane_records, budget_b, public_demo, strategy, now)
        ordered = sorted(candidates, key=lambda record: self._score(record, strategy, now), reverse=True)
        primary = ordered[0] if ordered else None
        fallbacks = ordered[1:4]
        if primary:
            reason = self._decision_reason(primary, strategy, public_demo)
            cost_hint = primary.cost_hint
            quota_impact = self._quota_impact(primary, now)
        else:
            reason = "No eligible helper model for lane after budget, license, health, and quota filters."
            cost_hint = "blocked"
            quota_impact = {"status": "blocked"}

        return LaneDecision(
            lane=lane,
            strategy=strategy,
            primary=primary,
            fallbacks=fallbacks,
            reason=reason,
            expected_cost_hint=cost_hint,
            quota_impact=quota_impact,
            context_packet=context,
            skipped=skipped,
        )

    def record_success(self, model_id: str, latency_ms: int | None = None) -> None:
        record = self._require_model(model_id)
        now = self._now()
        self._prune_calls(record, now)
        record.minute_calls.append(now)
        record.day_calls.append(now)
        record.success_count += 1
        record.last_failure = None
        record.health = "healthy"
        if latency_ms is not None:
            record.latency_ms = int((record.latency_ms * 0.7) + (latency_ms * 0.3))

    def record_failure(self, model_id: str, error: str = "execution failed") -> None:
        record = self._require_model(model_id)
        record.failure_count += 1
        record.last_failure = error
        record.health = "degraded" if record.failure_count < 3 else "unhealthy"
        if record.failure_count >= 3:
            self.enter_cooldown(model_id, retry_after_seconds=300)

    def enter_cooldown(self, model_id: str, retry_after_seconds: int = 60) -> None:
        record = self._require_model(model_id)
        record.cooldown_until = self._now() + timedelta(seconds=retry_after_seconds)

    def metadata_lookup(self, key: str, resolver: Callable[[], Any], ttl_seconds: int = 300) -> Any:
        now = self._now()
        cached = self._dedup.get(key)
        if cached and cached.expires_at > now:
            self._dedup_hits += 1
            return cached.value
        value = resolver()
        self._dedup[key] = _DedupEntry(value=value, expires_at=now + timedelta(seconds=ttl_seconds))
        return value

    def get_rotation_status(self) -> dict[str, Any]:
        now = self._now()
        for record in self.records.values():
            self._prune_calls(record, now)
        pinned = {record.lane: record.to_dict(now) for record in self.records.values() if record.pinned}
        lanes = {}
        for lane in sorted(PINNED_LANES | ROTATABLE_LANES):
            lane_records = [record for record in self.records.values() if record.lane == lane]
            if not lane_records:
                continue
            blocked = [record for record in lane_records if self._quota_blocked(record, now) or record.in_cooldown(now)]
            lanes[lane] = {
                "pinned": lane in PINNED_LANES,
                "models": len(lane_records),
                "blocked": len(blocked),
                "healthy": sum(1 for record in lane_records if record.health == "healthy"),
            }
        rotation_safe = all(record.health != "unhealthy" and not record.in_cooldown(now) for record in self.records.values() if record.pinned)
        return {
            "rotation_safe": rotation_safe,
            "pinned": pinned,
            "lanes": lanes,
            "dedup_cache_size": len(self._dedup),
            "dedup_hits": self._dedup_hits,
            "updated_at": _iso(now),
        }

    def dashboard_snapshot(self, public_demo: bool = True) -> dict[str, Any]:
        status = self.get_rotation_status()
        preview_lanes = [
            ("prompt_router", "strict tool JSON and prompt routing", "latency_first"),
            ("taste_judge", "taste/profile checkpoint", "quality_first"),
            ("audio_lore_tts", "optional lore narration, off by default", "license_safe_public" if public_demo else "quality_first"),
            ("hf_catalog_research", "HF metadata search/cache", "quota_saver"),
            ("modal_job_runner", "Modal credit jobs and LoRA evaluation", "private_research" if not public_demo else "license_safe_public"),
        ]
        status["decisions"] = [
            self.select_lane(lane, task=task, public_demo=public_demo, strategy=strategy).to_dict(self._now())
            for lane, task, strategy in preview_lanes
        ]
        return status

    @staticmethod
    def normalize_strategy(strategy: str) -> str:
        lowered = strategy.strip().lower()
        normalized = STRATEGY_ALIASES.get(lowered, lowered)
        allowed = {"quality_first", "quota_saver", "latency_first", "license_safe_public", "private_research"}
        return normalized if normalized in allowed else "quality_first"

    @staticmethod
    def normalize_lane(lane: str) -> str:
        normalized = lane.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "image": "image_generation",
            "locate": "grounding",
            "st3gg": "security",
            "router": "prompt_router",
            "judge": "taste_judge",
            "tts": "audio_lore_tts",
            "catalog": "hf_catalog_research",
            "modal": "modal_job_runner",
        }
        return aliases.get(normalized, normalized)

    def _eligible_records(
        self,
        records: list[ModelRecord],
        budget_b: float,
        public_demo: bool,
        strategy: str,
        now: datetime,
    ) -> tuple[list[ModelRecord], list[str]]:
        eligible: list[ModelRecord] = []
        skipped: list[str] = []
        require_public_safe = public_demo or strategy == "license_safe_public"
        for record in records:
            self._prune_calls(record, now)
            if record.pinned:
                skipped.append(f"{record.model_id}: pinned lane cannot rotate")
                continue
            if record.health in {"excluded", "unhealthy"}:
                skipped.append(f"{record.model_id}: health={record.health}")
                continue
            if record.params_b > budget_b:
                skipped.append(f"{record.model_id}: {record.params_b:.2f}B exceeds {budget_b:.2f}B helper budget")
                continue
            if require_public_safe and not record.public_safe:
                skipped.append(f"{record.model_id}: license gate {record.license_gate} excluded for public demo")
                continue
            if record.in_cooldown(now):
                skipped.append(f"{record.model_id}: cooldown active until {_iso(record.cooldown_until)}")
                continue
            if self._quota_blocked(record, now):
                record.cooldown_until = now + timedelta(seconds=60)
                skipped.append(f"{record.model_id}: quota exhausted, cooldown entered")
                continue
            eligible.append(record)
        return eligible, skipped

    def _score(self, record: ModelRecord, strategy: str, now: datetime) -> float:
        rpm_headroom = 1.0 - (len(record.minute_calls) / max(record.rpm_limit, 1))
        rpd_headroom = 1.0 - (len(record.day_calls) / max(record.rpd_limit, 1))
        quota_headroom = max(0.0, (rpm_headroom + rpd_headroom) / 2)
        latency_score = 1.0 / max(record.latency_ms, 1)
        provider_bonus = 0.06 if record.provider in {"local", "hf_cli", "hf_api"} else 0.0
        public_bonus = 0.08 if record.public_safe else 0.0
        health_penalty = 0.12 if record.health == "degraded" else 0.0

        if strategy == "quota_saver":
            return (quota_headroom * 0.46) + (provider_bonus * 2.0) + (latency_score * 40.0) + (record.quality_score * 0.18) - health_penalty
        if strategy == "latency_first":
            return (latency_score * 250.0) + (record.quality_score * 0.28) + (quota_headroom * 0.20) + provider_bonus - health_penalty
        if strategy == "license_safe_public":
            return (public_bonus * 2.0) + (record.quality_score * 0.55) + (quota_headroom * 0.25) + (latency_score * 40.0) - health_penalty
        if strategy == "private_research":
            private_bonus = 0.06 if record.license_gate in PRIVATE_LICENSES else 0.0
            return (record.quality_score * 0.88) + (quota_headroom * 0.10) + (latency_score * 5.0) + private_bonus - health_penalty
        return (record.quality_score * 0.64) + (quota_headroom * 0.20) + (latency_score * 30.0) + public_bonus - health_penalty

    def _decision_reason(self, primary: ModelRecord, strategy: str, public_demo: bool) -> str:
        if strategy == "license_safe_public":
            return f"{primary.model_id} selected because it is public-demo safe and within helper budget."
        if strategy == "quota_saver":
            return f"{primary.model_id} selected to preserve provider quota and reuse cheaper metadata paths."
        if strategy == "latency_first":
            return f"{primary.model_id} selected for fast dashboard feedback."
        if strategy == "private_research" and not public_demo:
            return f"{primary.model_id} selected for private research quality; public export gates still apply."
        return f"{primary.model_id} selected by quality-first helper rotation."

    def _quota_impact(self, record: ModelRecord | None, now: datetime) -> dict[str, Any]:
        if record is None:
            return {"status": "blocked"}
        self._prune_calls(record, now)
        return {
            "status": "ready" if not self._quota_blocked(record, now) and not record.in_cooldown(now) else "limited",
            "provider": record.provider,
            "rpm_used": len(record.minute_calls),
            "rpm_limit": record.rpm_limit,
            "rpd_used": len(record.day_calls),
            "rpd_limit": record.rpd_limit,
            "cooldown_until": _iso(record.cooldown_until),
        }

    def _quota_blocked(self, record: ModelRecord, now: datetime) -> bool:
        self._prune_calls(record, now)
        return len(record.minute_calls) >= record.rpm_limit or len(record.day_calls) >= record.rpd_limit

    def _prune_calls(self, record: ModelRecord, now: datetime) -> None:
        minute_cutoff = now - timedelta(minutes=1)
        day_cutoff = now - timedelta(days=1)
        record.minute_calls = [stamp for stamp in record.minute_calls if stamp > minute_cutoff]
        record.day_calls = [stamp for stamp in record.day_calls if stamp > day_cutoff]
        if record.cooldown_until and record.cooldown_until <= now:
            record.cooldown_until = None

    def _require_model(self, model_id: str) -> ModelRecord:
        try:
            return self.records[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model_id: {model_id}") from exc

    def _now(self) -> datetime:
        value = self._now_fn()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def default_model_records() -> list[ModelRecord]:
    return [
        ModelRecord(
            model_id="flux2-klein-primary",
            lane="image_generation",
            provider="hf",
            repo_id="black-forest-labs/FLUX.2-klein-9B",
            license_gate="review_required",
            params_b=9.0,
            cost_hint="provider_or_local",
            rpm_limit=8,
            rpd_limit=60,
            quality_score=0.96,
            latency_ms=26000,
            pinned=True,
        ),
        ModelRecord(
            model_id="locateanything-3b-anchor",
            lane="grounding",
            provider="hf_nvidia",
            repo_id="nvidia/LocateAnything-3B",
            license_gate="review_required",
            params_b=3.83,
            cost_hint="provider_or_local",
            rpm_limit=30,
            rpd_limit=300,
            quality_score=0.92,
            latency_ms=1800,
            pinned=True,
        ),
        ModelRecord(
            model_id="st3gg-local-scan",
            lane="security",
            provider="local",
            repo_id="ST3GG/local-defensive-scan",
            license_gate="internal",
            params_b=0.0,
            cost_hint="local",
            rpm_limit=10000,
            rpd_limit=100000,
            quality_score=0.9,
            latency_ms=20,
            pinned=True,
        ),
        ModelRecord(
            model_id="functiongemma-270m-router",
            lane="prompt_router",
            provider="local",
            repo_id="onnx-community/functiongemma-270m-it-ONNX",
            license_gate="gemma",
            params_b=0.27,
            cost_hint="local_free",
            rpm_limit=240,
            rpd_limit=10000,
            quality_score=0.74,
            latency_ms=80,
            fallback_chain=("minicpm5-1b-router", "qwen3-0.6b-router"),
        ),
        ModelRecord(
            model_id="minicpm5-1b-router",
            lane="prompt_router",
            provider="hf",
            repo_id="openbmb/MiniCPM5-1B",
            license_gate="apache-2.0",
            params_b=1.08,
            cost_hint="free_tier",
            rpm_limit=60,
            rpd_limit=1000,
            quality_score=0.79,
            latency_ms=160,
            fallback_chain=("functiongemma-270m-router", "qwen3-0.6b-router"),
        ),
        ModelRecord(
            model_id="qwen3-0.6b-router",
            lane="prompt_router",
            provider="hf",
            repo_id="Qwen/Qwen3-0.6B",
            license_gate="apache-2.0",
            params_b=0.60,
            cost_hint="free_tier",
            rpm_limit=60,
            rpd_limit=1000,
            quality_score=0.72,
            latency_ms=130,
        ),
        ModelRecord(
            model_id="netlify-ai-gateway-helper",
            lane="prompt_router",
            provider="netlify",
            repo_id="netlify/ai-gateway",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="optional_gateway_secret_required",
            rpm_limit=0,
            rpd_limit=0,
            quality_score=0.76,
            latency_ms=320,
            health="excluded",
        ),
        ModelRecord(
            model_id="cloudflare-agent-helper",
            lane="prompt_router",
            provider="cloudflare",
            repo_id="cloudflare/agents-sdk",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="optional_post_mvp_agent",
            rpm_limit=0,
            rpd_limit=0,
            quality_score=0.72,
            latency_ms=280,
            health="excluded",
        ),
        ModelRecord(
            model_id="offellia-gemma4-12b-private",
            lane="taste_judge",
            provider="local",
            repo_id="Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf",
            license_gate="private_research",
            params_b=12.0,
            cost_hint="local_gpu",
            rpm_limit=20,
            rpd_limit=200,
            quality_score=0.95,
            latency_ms=4200,
            fallback_chain=("nemotron-mini-4b-judge", "smolvlm2-2.2b-judge"),
        ),
        ModelRecord(
            model_id="nemotron-mini-4b-judge",
            lane="taste_judge",
            provider="hf_nvidia",
            repo_id="nvidia/Nemotron-Mini-4B-Instruct",
            license_gate="public_safe",
            params_b=4.0,
            cost_hint="free_tier_or_provider",
            rpm_limit=35,
            rpd_limit=600,
            quality_score=0.86,
            latency_ms=900,
            fallback_chain=("smolvlm2-2.2b-judge", "functiongemma-270m-judge-lite"),
        ),
        ModelRecord(
            model_id="smolvlm2-2.2b-judge",
            lane="taste_judge",
            provider="hf",
            repo_id="HuggingFaceTB/SmolVLM2-2.2B-Instruct",
            license_gate="apache-2.0",
            params_b=2.2,
            cost_hint="free_tier",
            rpm_limit=45,
            rpd_limit=800,
            quality_score=0.81,
            latency_ms=760,
        ),
        ModelRecord(
            model_id="functiongemma-270m-judge-lite",
            lane="taste_judge",
            provider="local",
            repo_id="onnx-community/functiongemma-270m-it-ONNX",
            license_gate="gemma",
            params_b=0.27,
            cost_hint="local_free",
            rpm_limit=240,
            rpd_limit=10000,
            quality_score=0.64,
            latency_ms=90,
        ),
        ModelRecord(
            model_id="dia-1.6b-tts",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="nari-labs/Dia-1.6B",
            license_gate="review_required",
            params_b=1.6,
            cost_hint="free_tier_or_modal",
            rpm_limit=25,
            rpd_limit=300,
            quality_score=0.88,
            latency_ms=2100,
        ),
        ModelRecord(
            model_id="vibevoice-1.5b-tts",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="microsoft/VibeVoice-1.5B",
            license_gate="review_required",
            params_b=1.5,
            cost_hint="free_tier_or_modal",
            rpm_limit=25,
            rpd_limit=300,
            quality_score=0.85,
            latency_ms=1900,
        ),
        ModelRecord(
            model_id="qwen3-tts-1.7b",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="Qwen/Qwen3-TTS-1.7B",
            license_gate="review_required",
            params_b=1.7,
            cost_hint="free_tier_or_modal",
            rpm_limit=25,
            rpd_limit=300,
            quality_score=0.84,
            latency_ms=1800,
        ),
        ModelRecord(
            model_id="voxcpm2-tts",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="openbmb/VoxCPM2",
            license_gate="apache-2.0",
            params_b=2.4,
            cost_hint="free_tier_or_modal",
            rpm_limit=25,
            rpd_limit=300,
            quality_score=0.82,
            latency_ms=1700,
        ),
        ModelRecord(
            model_id="zonos-tts",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="Zyphra/Zonos-v0.1-transformer",
            license_gate="apache-2.0",
            params_b=1.6,
            cost_hint="free_tier_or_modal",
            rpm_limit=25,
            rpd_limit=300,
            quality_score=0.81,
            latency_ms=1600,
        ),
        ModelRecord(
            model_id="kokoro-82m-tts",
            lane="audio_lore_tts",
            provider="local",
            repo_id="hexgrad/Kokoro-82M",
            license_gate="apache-2.0",
            params_b=0.082,
            cost_hint="local_free",
            rpm_limit=240,
            rpd_limit=10000,
            quality_score=0.73,
            latency_ms=120,
        ),
        ModelRecord(
            model_id="chatterbox-tts",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="ResembleAI/chatterbox",
            license_gate="mit",
            params_b=0.5,
            cost_hint="free_tier",
            rpm_limit=40,
            rpd_limit=800,
            quality_score=0.76,
            latency_ms=420,
        ),
        ModelRecord(
            model_id="higgs-audio-v3-excluded",
            lane="audio_lore_tts",
            provider="hf",
            repo_id="bosonai/higgs-audio-v3",
            license_gate="commercial_required",
            params_b=4.0,
            cost_hint="paid_or_uncleared",
            rpm_limit=0,
            rpd_limit=0,
            quality_score=0.89,
            latency_ms=1800,
            health="excluded",
        ),
        ModelRecord(
            model_id="netflix-void-modal",
            lane="video_repair",
            provider="modal",
            repo_id="Netflix/VOID",
            license_gate="private_research",
            params_b=1.3,
            cost_hint="modal_credits",
            rpm_limit=10,
            rpd_limit=120,
            quality_score=0.84,
            latency_ms=12000,
            fallback_chain=("void-q5-offline",),
        ),
        ModelRecord(
            model_id="void-q5-offline",
            lane="video_repair",
            provider="local",
            repo_id="local/VOID-Q5-video-repair",
            license_gate="private_research",
            params_b=1.3,
            cost_hint="offline",
            rpm_limit=20,
            rpd_limit=200,
            quality_score=0.78,
            latency_ms=16000,
        ),
        ModelRecord(
            model_id="fal-media-adapter",
            lane="video_repair",
            provider="fal",
            repo_id="fal-ai/optional-media-generation",
            license_gate="commercial_required",
            params_b=0.0,
            cost_hint="optional_external_provider",
            rpm_limit=0,
            rpd_limit=0,
            quality_score=0.8,
            latency_ms=6000,
            health="excluded",
        ),
        ModelRecord(
            model_id="hf-api-metadata-cache",
            lane="hf_catalog_research",
            provider="hf_api",
            repo_id="huggingface/hub-api",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="free_tier_cached",
            rpm_limit=180,
            rpd_limit=3000,
            quality_score=0.86,
            latency_ms=240,
            fallback_chain=("hf-cli-model-search", "local-catalog-cache"),
        ),
        ModelRecord(
            model_id="hf-cli-model-search",
            lane="hf_catalog_research",
            provider="hf_cli",
            repo_id="huggingface/hub-cli",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="free_tier_cli",
            rpm_limit=60,
            rpd_limit=1000,
            quality_score=0.84,
            latency_ms=600,
        ),
        ModelRecord(
            model_id="local-catalog-cache",
            lane="hf_catalog_research",
            provider="local",
            repo_id="local/nexus-weaver-catalog-cache",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="local_cache",
            rpm_limit=10000,
            rpd_limit=100000,
            quality_score=0.65,
            latency_ms=6,
        ),
        ModelRecord(
            model_id="modal-lora-eval-runner",
            lane="modal_job_runner",
            provider="modal",
            repo_id="modal/nexus-lora-eval",
            license_gate="private_research",
            params_b=0.0,
            cost_hint="modal_251_credit",
            rpm_limit=20,
            rpd_limit=180,
            quality_score=0.87,
            latency_ms=30000,
            fallback_chain=("modal-dry-run-planner",),
        ),
        ModelRecord(
            model_id="modal-video-repair-batch",
            lane="modal_job_runner",
            provider="modal",
            repo_id="modal/nexus-video-repair-batch",
            license_gate="private_research",
            params_b=0.0,
            cost_hint="modal_251_credit",
            rpm_limit=10,
            rpd_limit=80,
            quality_score=0.82,
            latency_ms=45000,
        ),
        ModelRecord(
            model_id="modal-dry-run-planner",
            lane="modal_job_runner",
            provider="local",
            repo_id="local/modal-job-dry-run",
            license_gate="public_safe",
            params_b=0.0,
            cost_hint="local_free",
            rpm_limit=10000,
            rpd_limit=100000,
            quality_score=0.58,
            latency_ms=12,
        ),
    ]
