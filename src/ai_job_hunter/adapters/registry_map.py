"""Maps ATSType/AggregatorType -> adapter class. The one place pipeline.py
would otherwise need ATS-specific branching."""

from __future__ import annotations

from ai_job_hunter.adapters.aggregators.arbeitnow import ArbeitnowAdapter
from ai_job_hunter.adapters.aggregators.himalayas import HimalayasAdapter
from ai_job_hunter.adapters.aggregators.remoteok import RemoteOKAdapter
from ai_job_hunter.adapters.aggregators.remotive import RemotiveAdapter
from ai_job_hunter.adapters.aggregators.weworkremotely import WeWorkRemotelyAdapter
from ai_job_hunter.adapters.ashby import AshbyAdapter
from ai_job_hunter.adapters.bamboohr import BambooHRAdapter
from ai_job_hunter.adapters.base import BaseAggregatorAdapter, BaseATSAdapter
from ai_job_hunter.adapters.greenhouse import GreenhouseAdapter
from ai_job_hunter.adapters.lever import LeverAdapter
from ai_job_hunter.adapters.personio import PersonioAdapter
from ai_job_hunter.adapters.recruitee import RecruiteeAdapter
from ai_job_hunter.adapters.smartrecruiters import SmartRecruitersAdapter
from ai_job_hunter.adapters.workable import WorkableAdapter
from ai_job_hunter.models import AggregatorType, ATSType

ATS_ADAPTERS: dict[ATSType, type[BaseATSAdapter]] = {
    ATSType.GREENHOUSE: GreenhouseAdapter,
    ATSType.LEVER: LeverAdapter,
    ATSType.ASHBY: AshbyAdapter,
    ATSType.WORKABLE: WorkableAdapter,
    ATSType.SMARTRECRUITERS: SmartRecruitersAdapter,
    ATSType.BAMBOOHR: BambooHRAdapter,
    ATSType.RECRUITEE: RecruiteeAdapter,
    ATSType.PERSONIO: PersonioAdapter,
    # ATSType.UNSUPPORTED intentionally has no entry — pipeline.py skips it.
}

AGGREGATOR_ADAPTERS: dict[AggregatorType, type[BaseAggregatorAdapter]] = {
    AggregatorType.REMOTEOK: RemoteOKAdapter,
    AggregatorType.ARBEITNOW: ArbeitnowAdapter,
    AggregatorType.REMOTIVE: RemotiveAdapter,
    AggregatorType.HIMALAYAS: HimalayasAdapter,
    AggregatorType.WEWORKREMOTELY: WeWorkRemotelyAdapter,
}
