def test_task_registered():
    from app.worker import celery_app
    from app.tasks.analysis_task import run_full_analysis

    assert run_full_analysis.name in celery_app.tasks


def test_celery_app_has_correct_broker():
    from app.worker import celery_app
    from app.config import get_settings

    settings = get_settings()
    assert celery_app.conf.broker_url == settings.redis_url


def test_task_has_correct_name():
    from app.tasks.analysis_task import run_full_analysis

    assert run_full_analysis.name == "app.tasks.analysis_task.run_full_analysis"
