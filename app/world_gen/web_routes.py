"""FastAPI routes of the author-side world generation page (token protected: everything lives under /api/inner).

  GET  /api/inner/worldgen/options[?refresh_gpu=1]   presets, defaults, ranges, GPU status, estimates, memory gate
  GET  /api/inner/worldgen/jobs                      job list (newest first)
  POST /api/inner/worldgen/jobs                      start a job (WorldGenRequest); 409 busy / memory / GPU, 422 bad params
  GET  /api/inner/worldgen/jobs/{id}                 status, stages, log tail, result, preview names
  POST /api/inner/worldgen/jobs/{id}/cancel          cancel (kills the running child process tree)
  GET  /api/inner/worldgen/jobs/{id}/preview/{name}  overview | relief | td  (PNG)

The manager is read from request.app.state.worldgen on every call so tests can swap it.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .web_jobs import WorldGenRefused, WorldGenRequest


def install(app):
    def mgr(request):
        return request.app.state.worldgen

    @app.exception_handler(WorldGenRefused)
    async def refused(request, error):
        return JSONResponse({'detail': error.detail}, status_code=error.status)

    @app.get('/api/inner/worldgen/options')
    async def worldgen_options(request: Request, refresh_gpu: bool = False):
        return await run_in_threadpool(mgr(request).options, refresh_gpu)

    @app.get('/api/inner/worldgen/jobs')
    def worldgen_jobs(request: Request):
        return mgr(request).list()

    @app.post('/api/inner/worldgen/jobs')
    async def worldgen_submit(request: Request, req: WorldGenRequest):
        return await run_in_threadpool(mgr(request).submit, req)

    @app.get('/api/inner/worldgen/jobs/{job_id}')
    def worldgen_job(request: Request, job_id: str):
        return mgr(request).view(job_id)

    @app.post('/api/inner/worldgen/jobs/{job_id}/cancel')
    async def worldgen_cancel(request: Request, job_id: str):
        return await run_in_threadpool(mgr(request).cancel, job_id)

    @app.post('/api/inner/worldgen/jobs/{job_id}/continue')
    async def worldgen_continue(request: Request, job_id: str):
        return await run_in_threadpool(mgr(request).continue_job, job_id)

    @app.get('/api/inner/worldgen/jobs/{job_id}/preview/{name}')
    def worldgen_preview(request: Request, job_id: str, name: str):
        return FileResponse(mgr(request).preview_path(job_id, name), media_type='image/png')
