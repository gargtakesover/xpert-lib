# Agent Directive Protocol: Jules

## Sandbox Constraints (CRITICAL)
**Jules operates within a highly restrictive sandboxed container.**
- You **DO NOT** have internet access or network capabilities.
- You **CANNOT** use `curl`, hit live X.com APIs, or communicate with remote Nitter Docker containers.
- Do not attempt to spin up network instances or pull Docker images.

## Testing & Verification Directives
Because of your sandbox constraints, executing the standard `pytest` integration suite will instantly cause Connection Timeout failures and hang your process execution.
**You must adhere to the following strict testing protocols:**
1. **Mocked Offline Validation Only:** When verifying your DOM extraction or logic changes, you must rely exclusively on offline, mocked tests (e.g., `tests/test_scraper_mocked.py`). You are encouraged to create synthetic, hardcoded HTML fixture string payloads to test your soup parsing functions!
2. **Targeted Sub-Testing:** Never run `pytest tests/` globally. Only ever execute the exact unitary test relevant to your current chunk of changes to prove the mathematical logic operates cleanly isolated from the web.
3. **Run What You Touch:** Do not analyze or execute the entire codebase test suite. Just test the literal files and logic diffs you generated. 

## Xpert Architectural Guidelines
1. **Data Minimization:** Keep LLM compatibility in mind. Any new extraction schemas (`community_note`, etc.) must pass cleanly through the `_clean_dict` routines inside `exporters.py` to seamlessly strip `Null` arrays.
2. **Jitter Protection:** Do not modify `CURRENT_DELAY` configuration overrides. We rely on randomized human mimicry natively on all outer requests.
3. **800-Tweet Ceilings:** The `limit` parameters must securely cap out horizontally at 800 per timeline query. Do not force unbounded loops.

## Guides
To make sure that th script you create works you need to analyze nitter'c code to understand which information of tweets or profiles will be available where.