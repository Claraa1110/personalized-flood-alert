"""Pins the background job configuration.

The scheduler is the only thing that turns rainfall into alerts, so its
cadence and job set are part of the product's safety contract.
"""

from app.scheduler import setup_scheduler


def _jobs() -> dict:
    scheduler = setup_scheduler()
    return {job.id: job for job in scheduler.get_jobs()}


def test_registers_the_three_expected_jobs():
    assert set(_jobs()) == {"fetch_rainfall", "evaluate_risk", "cleanup"}


def test_rainfall_and_risk_evaluation_run_every_ten_minutes():
    jobs = _jobs()
    for job_id in ("fetch_rainfall", "evaluate_risk"):
        assert str(jobs[job_id].trigger.interval) == "0:10:00", job_id


def test_long_running_jobs_cannot_overlap_themselves():
    jobs = _jobs()
    assert jobs["fetch_rainfall"].max_instances == 1
    assert jobs["evaluate_risk"].max_instances == 1


def test_cleanup_runs_daily_in_the_small_hours():
    trigger = _jobs()["cleanup"].trigger
    assert "hour='3'" in str(trigger)


def test_setup_is_idempotent():
    # ``replace_existing=True`` means a second call must not duplicate jobs.
    setup_scheduler()
    assert len(_jobs()) == 3


def test_news_ingestion_is_not_scheduled():
    """Characterisation: the news pipeline exists but never runs in production.

    ``news_service.fetch_news`` and the LLM location extraction are only
    reachable from ``scripts/``. ``news_articles`` therefore stays empty, and
    ``risk_engine.get_news_signal_near`` - which queries it - is dead code
    that is never called from the evaluation loop either. Tracked as
    ROADMAP P2-3.
    """
    assert "fetch_news" not in _jobs()


def test_push_delivery_is_not_a_separate_job():
    # Pushes are sent inline at the end of evaluate_all_properties, so a slow
    # or hanging Expo call delays the next evaluation cycle.
    assert "send_push" not in _jobs()
