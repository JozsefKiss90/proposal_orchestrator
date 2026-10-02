# -*- coding: utf-8 -*-
import json, math, os

OUT = r"C:/Code/proposal_demo/proposal_orchestrator/.ua/intermediate"
META = json.load(open(r"C:/Code/proposal_demo/proposal_orchestrator/.ua/intermediate/batchmeta/batch-5-meta.json"))
BID = META["batchImportData"]

nodes = []
edges = []

def fnode(path, name, summary, tags, complexity, notes=None):
    n = {"id": "file:"+path, "type": "file", "name": name, "filePath": path,
         "summary": summary, "tags": tags, "complexity": complexity}
    if notes: n["languageNotes"] = notes
    nodes.append(n)

def sub(kind, path, name, rng, summary, tags, complexity, notes=None):
    n = {"id": "%s:%s:%s" % (kind, path, name), "type": kind, "name": name,
         "filePath": path, "lineRange": rng, "summary": summary,
         "tags": tags, "complexity": complexity}
    if notes: n["languageNotes"] = notes
    nodes.append(n)
    edges.append({"source": "file:"+path, "target": n["id"], "type": "contains",
                  "direction": "forward", "weight": 1.0})
    if not name.startswith("_"):
        edges.append({"source": "file:"+path, "target": n["id"], "type": "exports",
                      "direction": "forward", "weight": 0.8})

# ---------------------------------------------------------------- claude_transport
P = "runner/claude_transport.py"
fnode(P, "claude_transport.py",
 "Sole runtime transport boundary for Claude invocations: subprocesses the local `claude` CLI in print mode, reassembles the response from multi-turn stream-json output, and enforces timeouts with a full process-tree kill. Authenticated by the user's Claude Code Max subscription, so no Anthropic API key is involved.",
 ["transport","subprocess","llm-invocation","timeout-handling","entry-point"], "complex",
 "Platform-split Popen kwargs (POSIX new session vs Windows no-window creation flags) plus a stdin writer thread are what make the CLI child both drainable and killable as a tree.")
sub("class",P,"ClaudeTransportError",[48,68],
 "Base transport exception carrying the diagnostic context of a failed CLI invocation - the command, exit code and captured output.",
 ["error-handling","exception","transport"],"simple")
sub("class",P,"ClaudeCLIUnavailableError",[71,72],
 "Raised when no `claude` executable can be resolved at all, distinguishing a missing CLI from a failed invocation.",
 ["error-handling","exception","transport"],"simple")
sub("class",P,"ClaudeCLIRateLimitError",[75,100],
 "Raised when the CLI reports subscription usage-limit exhaustion, carrying the detected rate-limit notice line for the operator.",
 ["error-handling","exception","rate-limiting"],"simple")
sub("class",P,"ClaudeCLITimeoutError",[103,123],
 "Raised when the CLI exceeds its invocation timeout, carrying the elapsed time and the process-tree snapshot taken before the kill.",
 ["error-handling","exception","timeout-handling"],"simple")
sub("class",P,"ClaudeCLIResolution",[267,286],
 "NamedTuple recording how the `claude` executable was resolved - the absolute path and whether it came from the environment pin or the OS search path.",
 ["data-model","configuration","transport"],"simple")
sub("class",P,"AssistantTurn",[432,446],
 "NamedTuple for one assistant turn parsed out of stream-json, carrying its text and whether it is a restart-style continuation of a truncated turn.",
 ["data-model","parsing","transport"],"simple")
sub("function",P,"_effective_max_output_tokens",[171,194],
 "Resolves the output-token ceiling handed to the CLI, preferring a positive ORCHESTRATOR_MAX_OUTPUT_TOKENS override and ignoring an invalid value with a warning rather than passing it through.",
 ["configuration","validation","transport"],"simple")
sub("function",P,"_rate_limit_notice",[239,254],
 "Scans stdout and stderr line by line for usage-limit signals and returns the first matching line, surfacing subscription quota exhaustion as a human-readable notice.",
 ["rate-limiting","diagnostics","transport"],"simple")
sub("function",P,"resolve_claude_cli",[295,373],
 "Resolves which `claude` executable to spawn, honouring the ORCHESTRATOR_CLAUDE_CLI_PATH pin (quotes stripped, `~` and env vars expanded) before falling back to the OS search path.",
 ["configuration","path-resolution","transport"],"moderate")
sub("function",P,"_announce_cli_resolution",[376,406],
 "Logs the resolved executable once per distinct path, so a run record names which installed CLI build served its invocations.",
 ["logging","diagnostics","transport"],"simple")
sub("function",P,"_splice_continuation",[449,497],
 "Splices a restart-style continuation onto a truncated turn: when an output-token cut lands inside a fenced block the CLI re-opens the fence and re-emits the element, so the overlap must be detected rather than appended.",
 ["parsing","truncation-recovery","transport"],"moderate")
sub("function",P,"_join_assistant_turns",[500,537],
 "Joins assistant turns with no separator so a turn split mid-token rejoins seamlessly, with restart continuations spliced instead of concatenated.",
 ["parsing","text-assembly","transport"],"moderate")
sub("function",P,"_reassemble_stream_json",[540,617],
 "Rebuilds the complete assistant-visible text from `--output-format stream-json` events, recovering every assistant turn rather than only the final message the CLI's text mode prints.",
 ["parsing","stream-json","transport"],"moderate")
sub("function",P,"_tree_killable_popen_kwargs",[625,647],
 "Platform-specific Popen keyword arguments that make the spawned CLI tree signalable as a group - a new session on POSIX, no-window creation flags on Windows.",
 ["process-management","cross-platform","transport"],"simple")
sub("function",P,"_kill_process_tree",[650,692],
 "Forcibly terminates the child and every descendant including the CLI's Node subtree, because Python's own timeout handling kills only the direct child and orphans the rest.",
 ["process-management","timeout-handling","transport"],"moderate")
sub("function",P,"_child_tree_snapshot",[695,772],
 "Best-effort process-tree snapshot taken on the timeout path before the kill, so a recurrence of the pre-main CLI stall records what the hung tree actually looked like.",
 ["diagnostics","process-management","transport"],"moderate")
sub("function",P,"_drain_after_kill",[775,787],
 "Drains and reaps the killed child's pipes to return any buffered output; it never raises, so a drain failure cannot mask the transport error being surfaced.",
 ["process-management","error-handling","transport"],"simple")
sub("function",P,"invoke_claude_text",[795,1062],
 "The single public transport entry point: builds the `claude -p` argument vector, streams the prompt over stdin, reassembles the response, and raises typed transport errors on timeout, non-zero exit, empty output or a missing CLI.",
 ["transport","llm-invocation","subprocess","entry-point"],"complex")

# ---------------------------------------------------------------- json_extract
P = "runner/json_extract.py"
fnode(P, "json_extract.py",
 "Pure string-to-JSON helper that recovers the first JSON object from a model response - bare, fenced, or wrapped in prose - shared by the semantic dispatcher and the out-of-band harness judge. It never repairs: an unparseable response yields None and the caller decides what that means.",
 ["utility","parsing","json","llm-response","shared-helper"], "simple")
sub("function",P,"extract_first_json_object",[33,74],
 "Returns the first top-level JSON object in a response by trying the whole string, then a fenced block, then the first brace span; rejects a nested object pulled out of a top-level array and never raises or repairs malformed input.",
 ["utility","parsing","json","validation"],"simple")

# ---------------------------------------------------------------- semantic_dispatch
P = "runner/semantic_dispatch.py"
fnode(P, "semantic_dispatch.py",
 "Dispatches each semantic gate predicate to its designated agent through the runtime transport: reads the artifacts under evaluation, builds a system prompt stating the constitutional rule and the mandatory result schema, and returns the agent's structured verdict. Dispatch failures become schema-valid fail results flagged `_dispatch_error`, never fabricated passes.",
 ["semantic-dispatch","gate-evaluation","llm-invocation","validation","transport"], "complex",
 "No local rule about what constitutes a violation is encoded here - the agent reasons from the artifact content and the rule quoted in its system prompt.")
sub("class",P,"SemanticPredicateConfig",[110,122],
 "Dataclass describing one semantic predicate - its function name, designated agent, description, and the constitutional rule it enforces.",
 ["data-model","configuration","semantic-dispatch"],"simple")
sub("function",P,"validate_semantic_result",[222,294],
 "Validates an agent result against the result schema, rejecting any `fail` finding that omits `violated_rule` or `evidence_path` and returning a machine-readable reason for every rejection.",
 ["validation","schema","semantic-dispatch"],"moderate")
sub("function",P,"_dispatch_error_result",[302,338],
 "Builds a schema-valid fail result with `_dispatch_error: True` and empty findings, so a transport or parse failure surfaces as a gate failure with its real cause rather than as a semantic verdict.",
 ["error-handling","fail-closed","semantic-dispatch"],"moderate")
sub("function",P,"_write_semantic_diagnostics",[341,435],
 "Writes a diagnostic bundle for a dispatch failure under `.claude/semantic_diag/`, mirroring the skill runtime's diagnostic pattern; a failure to write is swallowed rather than masking the original error.",
 ["diagnostics","error-handling","semantic-dispatch"],"moderate")
sub("function",P,"_read_artifacts",[438,480],
 "Reads artifact content from every string-valued predicate arg, expanding a directory arg to its direct-child JSON files and silently skipping absent paths - presence is the deterministic layer's responsibility.",
 ["io","artifact-resolution","semantic-dispatch"],"moderate")
sub("function",P,"_build_system_prompt",[504,541],
 "Builds the agent system prompt stating its constitutional role, the predicate to evaluate, the rule it enforces, and the exact JSON schema the response must conform to.",
 ["prompt-assembly","semantic-dispatch","llm-invocation"],"moderate")
sub("function",P,"_build_user_prompt",[544,573],
 "Builds the user turn carrying the artifact content the agent must inspect.",
 ["prompt-assembly","semantic-dispatch","artifact-resolution"],"simple")
sub("function",P,"_extract_json",[576,585],
 "Thin wrapper delegating JSON recovery from the agent response to the shared extractor.",
 ["parsing","json","utility"],"simple")
sub("function",P,"_resolve_semantic_backend",[596,610],
 "Resolves and caches the transport backend for semantic predicates, sharing the skill runtime's provider resolution so production-mode enforcement applies equally here.",
 ["configuration","transport","caching"],"simple")
sub("function",P,"_invoke_via_backend",[613,683],
 "Routes the invocation to the Claude CLI, the native Bedrock Converse backend, or a generic OpenAI-compatible backend according to the resolved provider config, returning the raw response text.",
 ["transport","llm-invocation","backend-selection"],"moderate")
sub("function",P,"invoke_agent",[691,826],
 "Invokes the designated agent end to end - artifact reads, prompt assembly, backend invocation, JSON recovery - and returns the raw result dict for schema validation by the caller.",
 ["semantic-dispatch","llm-invocation","orchestration"],"complex")
sub("function",P,"dispatch_semantic_predicate",[834,863],
 "Public entry point called by the gate evaluator once deterministic predicates have passed; delegates to invoke_agent and leaves result validation to the caller.",
 ["semantic-dispatch","gate-evaluation","entry-point"],"simple")

# ---------------------------------------------------------------- skill_runtime
P = "runner/skill_runtime.py"
fnode(P, "skill_runtime.py",
 "Claude runtime transport adapter for skills: loads a skill `.md` specification, resolves canonical inputs from disk, assembles the prompt in TAPM or cli-prompt mode, invokes Claude, parses and validates the structured response against the artifact schema, writes canonical artifacts atomically, and returns a SkillResult. It holds no domain knowledge.",
 ["skill-runtime","transport","validation","prompt-assembly","artifact-writing"], "complex",
 "Skill `.md` files are specifications, not executable code - nothing here interprets them. Claude performs the reasoning; Python owns every write and never silently repairs a response.")
sub("class",P,"SkillRuntimeError",[166,174],
 "Exception raised for skill runtime configuration and loading failures, distinct from a SkillResult carrying a structured failure category.",
 ["error-handling","exception","skill-runtime"],"simple")
sub("function",P,"_run_id_echo_directive",[103,124],
 "Builds the directive instructing Claude to copy the run_id verbatim rather than retype it - a regenerated UUID looks plausible but is wrong, and the validator treats it as a failure.",
 ["prompt-assembly","validation","skill-runtime"],"simple")
sub("function",P,"_resolve_transport_backend",[136,151],
 "Resolves and caches the active transport backend from the ORCHESTRATOR_TRANSPORT_* environment, defaulting to the Claude CLI path when unset.",
 ["configuration","transport","caching"],"simple")
sub("function",P,"_load_skill_catalog",[184,208],
 "Loads and caches `skill_catalog.yaml`, the source of each skill's reads_from, writes_to and constitutional constraints.",
 ["configuration","caching","skill-runtime"],"simple")
sub("function",P,"_load_artifact_schemas",[228,255],
 "Loads and caches `artifact_schema_specification.yaml`, the authority for canonical artifact paths and their required fields.",
 ["configuration","schema","caching"],"simple")
sub("function",P,"_find_schema_for_path",[281,302],
 "Finds the artifact schema entry whose canonical_path matches a given path, searching every known schema section.",
 ["schema","lookup","skill-runtime"],"moderate")
sub("function",P,"_extract_schema_requirements",[305,319],
 "Extracts the schema_id value and the required field names from a schema entry.",
 ["schema","utility","skill-runtime"],"simple")
sub("function",P,"_sanitize_filename",[327,340],
 "Sanitizes a descriptor into a filesystem-safe component for diagnostic filenames.",
 ["utility","diagnostics","skill-runtime"],"simple")
sub("function",P,"_is_contextual_descriptor",[348,364],
 "Decides whether an input descriptor is contextual rather than a canonical artifact path, so context-only inputs are not validated as artifacts on disk.",
 ["validation","classification","skill-runtime"],"simple")
sub("function",P,"_resolve_inputs",[382,423],
 "Reads the skill's declared `reads_from` artifacts from disk and merges them with caller-supplied inputs, keyed by repo-relative path.",
 ["io","artifact-resolution","skill-runtime"],"moderate")
sub("function",P,"_validate_skill_inputs",[426,480],
 "Verifies every declared input is present and non-empty, treating a path that is both read and written as an upsert target where an empty object is a valid initial state.",
 ["validation","fail-closed","skill-runtime"],"moderate")
sub("function",P,"_anchor_field",[494,507],
 "Returns the first required non-metadata field of a schema - the key a multi-artifact response is anchored on, by both the prompt directive and the canonical writer, so the two must agree.",
 ["schema","multi-artifact","skill-runtime"],"simple")
sub("function",P,"_artifacts_under_directory",[510,537],
 "Searches the artifact schema sections for every canonical artifact living under a directory path, returning each with its schema entry.",
 ["schema","artifact-resolution","skill-runtime"],"moderate")
sub("function",P,"_resolve_output_artifacts",[540,564],
 "Expands a `writes_to` entry into the canonical artifacts it covers - a directory fanning out to every artifact beneath it - dropping entries that resolve to nothing.",
 ["schema","artifact-resolution","skill-runtime"],"moderate")
sub("function",P,"_collect_schema_hints",[567,596],
 "Resolves `writes_to` into ordered canonical schema hints - path, schema_id and required fields - and reports whether any schema requires a run_id. The field order is part of the contract.",
 ["schema","prompt-assembly","skill-runtime"],"moderate")
sub("function",P,"_multi_artifact_directive",[599,641],
 "Builds the prompt directive naming the top-level anchor keys a multi-artifact response must carry, kept in agreement with how the canonical writer extracts each sub-artifact.",
 ["prompt-assembly","multi-artifact","skill-runtime"],"moderate")
sub("function",P,"_assemble_skill_prompt",[644,730],
 "Assembles the cli-prompt mode system and user prompts with every resolved input serialized inline.",
 ["prompt-assembly","skill-runtime","cli-prompt-mode"],"moderate")
sub("function",P,"_assemble_tapm_prompt",[733,898],
 "Assembles Tool-Augmented Prompt Mode prompts that pass declared input *paths* instead of serialized contents, so Claude reads them from disk through the Read tool and the prompt stays bounded.",
 ["prompt-assembly","tapm","skill-runtime"],"complex")
sub("function",P,"_invoke_claude",[906,925],
 "Invokes the shared Claude transport and returns either the response text or an error message, keeping transport exceptions out of the main control flow.",
 ["transport","llm-invocation","skill-runtime"],"simple")
sub("function",P,"_classify_transport_failure",[941,959],
 "Maps a transport exception onto a diagnostic failure class - timeout, non-zero exit, empty output, CLI unavailable, or other.",
 ["error-handling","classification","transport"],"simple")
sub("function",P,"_write_transport_failure_diagnostics",[962,1076],
 "Writes a uniform diagnostic bundle - structured meta JSON plus prompt and stdout/stderr companion files - for every transport failure class in both execution modes.",
 ["diagnostics","error-handling","skill-runtime"],"complex")
sub("function",P,"_json_break_point",[1090,1134],
 "Describes in one clause where a response stopped being valid JSON, so a break tens of thousands of characters in is actionable instead of reported as a generic non-JSON response.",
 ["diagnostics","parsing","error-reporting"],"moderate")
sub("function",P,"_extract_json_response",[1137,1290],
 "Extracts the artifact JSON from Claude's response, handling bare, fenced and prose-wrapped payloads and picking the real object by largest-span candidate competition so a fenced decoy from an intermediate turn cannot win.",
 ["parsing","json","llm-response","skill-runtime"],"complex")
sub("function",P,"_validate_skill_output",[1293,1370],
 "Checks a parsed skill response against its schema expectations: a missing or regenerated run_id, a wrong schema_id, or a present artifact_status are validation failures, never auto-corrected.",
 ["validation","schema","fail-closed","skill-runtime"],"moderate")
sub("function",P,"_atomic_write",[1378,1426],
 "Writes a canonical artifact atomically via a same-directory temp file plus read-back validation, so the canonical path is never left partially written.",
 ["io","atomic-write","artifact-writing"],"moderate")
sub("function",P,"run_skill",[1434,2739],
 "Executes one skill end to end - input validation, prompt assembly in the chosen mode, Claude invocation, response extraction, schema validation and atomic canonical writes - returning a SkillResult whose failure_category classifies any break in that chain.",
 ["skill-runtime","orchestration","entry-point","validation"],"complex")

# ---------------------------------------------------------------- transport/__init__
P = "runner/transport/__init__.py"
fnode(P, "__init__.py",
 "Barrel for the backend-agnostic transport package, re-exporting only the dependency-free surface - provider capabilities, provider config and presets, the error taxonomy, the tool executor and the tool loop - so importing the package never pulls in the optional httpx or boto3 clients.",
 ["barrel","entry-point","re-exports","transport"], "simple")

# ---------------------------------------------------------------- bedrock_converse
P = "runner/transport/bedrock_converse.py"
fnode(P, "bedrock_converse.py",
 "Native AWS Bedrock Converse backend implementing the ToolLoopBackend protocol through boto3, bypassing the OpenAI-compatible proxy and using the standard AWS credential chain plus inference profiles for on-demand throughput.",
 ["transport","backend","aws-bedrock","adapter","llm-invocation"], "moderate",
 "boto3 is imported inside a try/except so the module stays importable when the optional dependency is absent.")
sub("class",P,"BedrockConverseBackend",[47,342],
 "Callable backend that converts OpenAI-shaped messages and tool schemas into the Bedrock Converse format, invokes bedrock-runtime, extracts the response text and token usage, and classifies boto3 client errors into the shared transport taxonomy.",
 ["transport","aws-bedrock","adapter","error-handling"],"complex")

# ---------------------------------------------------------------- capabilities
P = "runner/transport/capabilities.py"
fnode(P, "capabilities.py",
 "Static per-provider capability metadata - streaming, tool calling, structured-output level, usage reporting, auth type and OpenAI compatibility - declared as a frozen dataclass registry with no dynamic detection or extra API calls.",
 ["configuration","metadata","data-model","transport"], "simple")
sub("class",P,"ProviderCapabilities",[23,52],
 "Frozen dataclass declaring one provider's static feature surface, consulted by the benchmark engine and the error-handling layer rather than negotiated at runtime.",
 ["data-model","configuration","transport"],"simple")

# ---------------------------------------------------------------- config
P = "runner/transport/config.py"
fnode(P, "config.py",
 "Resolves the ORCHESTRATOR_TRANSPORT_* environment (and named presets) into a ProviderConfig, selecting among the claude_cli, bedrock, bedrock_converse, together_ai, ollama and generic OpenAI-compatible backends, and constructs the chosen backend with optional imports deferred.",
 ["configuration","transport","backend-selection","factory","environment"], "complex",
 "The httpx and boto3 imports live inside the builder functions, so the default Claude CLI path never requires either dependency.")
sub("class",P,"TransportPreset",[102,148],
 "Frozen dataclass bundling a named preset's backend, endpoint, model, region and capability declarations.",
 ["data-model","configuration","presets"],"simple")
sub("class",P,"ProviderConfig",[300,323],
 "Resolved transport configuration - backend name, endpoint, model, credentials and capabilities - that the backend factories and callers consume.",
 ["data-model","configuration","transport"],"simple")
sub("function",P,"validate_bedrock_model_id",[331,341],
 "Checks a model identifier against the Bedrock `<provider>.<model>` format.",
 ["validation","aws-bedrock","configuration"],"simple")
sub("function",P,"is_production_mode",[349,351],
 "Reports whether production mode is active, which gates the set of admissible backends.",
 ["configuration","guard","transport"],"simple")
sub("function",P,"_enforce_production_backend",[354,369],
 "Rejects any non-production backend when production mode is active, raising ValueError rather than silently downgrading the transport.",
 ["validation","fail-closed","configuration"],"simple")
sub("function",P,"list_transport_presets",[377,379],
 "Returns the names of all registered transport presets.",
 ["configuration","presets","utility"],"simple")
sub("function",P,"get_transport_preset",[382,395],
 "Looks up a named transport preset, raising ValueError for an unrecognised name.",
 ["configuration","presets","lookup"],"simple")
sub("function",P,"resolve_provider_config_from_preset",[398,488],
 "Resolves a ProviderConfig from a named preset, letting explicit environment variables override preset defaults under a backend-safety rule that prevents a mismatched backend/endpoint pairing.",
 ["configuration","presets","transport"],"complex")
sub("function",P,"resolve_provider_config",[496,571],
 "Reads the transport environment and returns the resolved ProviderConfig, delegating to the preset resolver when ORCHESTRATOR_TRANSPORT_PRESET is set.",
 ["configuration","transport","entry-point"],"moderate")
sub("function",P,"_resolve_bedrock",[574,605],
 "Resolves Bedrock configuration for the bedrock-mantle OpenAI-compatible endpoint, constructing the regional URL and validating the model identifier.",
 ["configuration","aws-bedrock","transport"],"moderate")
sub("function",P,"_resolve_bedrock_converse",[608,620],
 "Resolves native Bedrock Converse configuration - region, model and inference profile - for the boto3 backend.",
 ["configuration","aws-bedrock","transport"],"simple")
sub("function",P,"_resolve_together_ai",[623,641],
 "Resolves Together AI endpoint, model and API-key configuration.",
 ["configuration","transport","provider"],"simple")
sub("function",P,"_resolve_ollama",[644,656],
 "Resolves local Ollama endpoint and model configuration, which needs no API key.",
 ["configuration","transport","provider"],"simple")
sub("function",P,"_resolve_generic",[659,678],
 "Resolves a generic OpenAI-compatible endpoint configuration from explicit environment variables.",
 ["configuration","transport","provider"],"moderate")
sub("function",P,"build_openai_backend",[686,752],
 "Constructs an OpenAICompatBackend from a resolved config, deferring the httpx import to the point a non-Claude backend is actually needed.",
 ["factory","transport","backend-selection"],"moderate")
sub("function",P,"build_converse_backend",[755,793],
 "Constructs a BedrockConverseBackend from a resolved bedrock_converse config, converting any OpenAI-format tool schemas internally.",
 ["factory","transport","aws-bedrock"],"moderate")

# ---------------------------------------------------------------- errors
P = "runner/transport/errors.py"
fnode(P, "errors.py",
 "Transport-layer error taxonomy for the OpenAI-compatible backends: an ErrorCategory enum aligned with the SkillResult failure categories, typed exceptions carrying retryability metadata, and an HTTP status-to-exception normalizer.",
 ["error-handling","exception","taxonomy","transport"], "simple")
sub("class",P,"ErrorCategory",[24,50],
 "String enum of transport failure categories - rate limited, provider error, auth failure, malformed request, model not found, timeout - each annotated with whether it is retryable.",
 ["error-handling","taxonomy","enum"],"simple")
sub("class",P,"OpenAICompatTransportError",[58,78],
 "Base transport exception for OpenAI-compatible backends, carrying its error category, retryability flag and a truncated response body for diagnostics.",
 ["error-handling","exception","transport"],"simple")
sub("class",P,"OpenAICompatAuthError",[81,82],
 "Raised on HTTP 401/403 or an AWS access-denied error; non-retryable.",
 ["error-handling","exception","authentication"],"simple")
sub("class",P,"OpenAICompatRateLimitError",[85,86],
 "Raised on HTTP 429 or a provider throttling exception; retryable.",
 ["error-handling","exception","rate-limiting"],"simple")
sub("class",P,"OpenAICompatProviderError",[89,90],
 "Raised on provider-side 5xx, service-unavailable or internal-failure responses; retryable.",
 ["error-handling","exception","transport"],"simple")
sub("class",P,"OpenAICompatTimeoutError",[93,94],
 "Raised when a provider request exceeds its timeout.",
 ["error-handling","exception","timeout-handling"],"simple")
sub("class",P,"OpenAICompatModelNotFoundError",[97,98],
 "Raised on HTTP 404 or a missing-resource error naming an unknown model; non-retryable.",
 ["error-handling","exception","configuration"],"simple")
sub("function",P,"normalize_http_error",[118,155],
 "Maps an HTTP status code and response body onto a typed transport exception carrying its category and retryability metadata.",
 ["error-handling","http","classification"],"moderate")

# ---------------------------------------------------------------- openai_compatible
P = "runner/transport/openai_compatible.py"
fnode(P, "openai_compatible.py",
 "HTTP backend implementing the ToolLoopBackend protocol by POSTing to any OpenAI Chat Completions endpoint - used for Bedrock via bedrock-mantle, Together AI and Ollama. Requires httpx, which the config factory imports lazily.",
 ["transport","backend","http-client","adapter","llm-invocation"], "moderate")
sub("class",P,"OpenAICompatBackend",[48,253],
 "Callable backend that builds the chat-completions payload, posts it with httpx, normalizes HTTP errors into the shared taxonomy, and extracts the message text, tool calls and token usage.",
 ["transport","http-client","adapter","error-handling"],"moderate")

# ---------------------------------------------------------------- tool_executor
P = "runner/transport/tool_executor.py"
fnode(P, "tool_executor.py",
 "Local Read/Glob tool executor that emulates the file access Claude Code provides natively, for non-Claude backends whose tool loop Python must drive. Read-only by construction, with path authorisation applied after symlink resolution and every denial returned as a structured tool error.",
 ["tool-execution","security","sandboxing","filesystem","transport"], "moderate",
 "Containment is checked with Path.resolve() plus Path.relative_to, which is what makes `../` escapes and symlink traversal out of the declared input roots impossible rather than merely detected.")
sub("class",P,"ToolExecutor",[165,393],
 "Honours or denies a model's Read/Glob tool calls against the repository root and the skill's declared input prefixes, tracking bytes read and files touched; it exposes no write, edit or delete tool at all.",
 ["tool-execution","security","sandboxing","filesystem"],"complex")
sub("function",P,"is_within",[136,152],
 "Returns whether a resolved path lies inside a resolved root - the symlink- and `../`-safe containment check every authorisation path depends on.",
 ["security","path-validation","utility"],"simple")

# ---------------------------------------------------------------- tool_loop
P = "runner/transport/tool_loop.py"
fnode(P, "tool_loop.py",
 "Drives the iterative request to tool_calls to execute to re-send cycle for backends without native Read/Glob support, bounded by a max-round limit and deliberately decoupled from any particular HTTP client.",
 ["tool-execution","loop","tapm","adapter","transport"], "moderate")
sub("class",P,"ToolLoopResponse",[61,81],
 "Dataclass capturing a loop outcome - the final text, rounds taken, tool calls executed and accumulated token usage.",
 ["data-model","tool-execution","transport"],"simple")
sub("class",P,"ToolLoopBackend",[89,112],
 "Protocol a backend must satisfy to be driven by the tool loop: callable on a message list, returning a response dict.",
 ["protocol","type-definition","transport"],"simple")
sub("class",P,"FakeBackend",[120,155],
 "Test double returning a pre-programmed sequence of responses, including synthetic tool calls, so the loop can be exercised without a live provider.",
 ["test-double","testing","tool-execution"],"simple")
sub("function",P,"run_tool_loop",[163,284],
 "Runs the tool-call loop against a backend callable, executing each honoured Read/Glob call through the sandboxed executor, injecting structured errors for unknown tool names or malformed arguments, and stopping after max_rounds to bound runaway model behaviour.",
 ["tool-execution","loop","fail-closed","transport"],"complex")

# ---------------------------------------------------------------- imports (1:1)
imp_total = 0
for src, targets in BID.items():
    for t in targets:
        edges.append({"source": "file:"+src, "target": "file:"+t, "type": "imports",
                      "direction": "forward", "weight": 0.7})
        imp_total += 1

# ---------------------------------------------------------------- calls / depends_on
CALLS = [
 ("function:runner/skill_runtime.py:_invoke_claude", "function:runner/claude_transport.py:invoke_claude_text"),
 ("function:runner/skill_runtime.py:_resolve_transport_backend", "function:runner/transport/config.py:resolve_provider_config"),
 ("function:runner/skill_runtime.py:run_skill", "function:runner/transport/tool_loop.py:run_tool_loop"),
 ("function:runner/skill_runtime.py:run_skill", "class:runner/transport/tool_executor.py:ToolExecutor"),
 ("function:runner/skill_runtime.py:run_skill", "class:runner/runtime_models.py:SkillResult"),
 ("function:runner/semantic_dispatch.py:_extract_json", "function:runner/json_extract.py:extract_first_json_object"),
 ("function:runner/semantic_dispatch.py:_invoke_via_backend", "function:runner/claude_transport.py:invoke_claude_text"),
 ("function:runner/semantic_dispatch.py:_invoke_via_backend", "function:runner/transport/config.py:build_openai_backend"),
 ("function:runner/semantic_dispatch.py:_invoke_via_backend", "function:runner/transport/config.py:build_converse_backend"),
 ("function:runner/semantic_dispatch.py:_resolve_semantic_backend", "function:runner/transport/config.py:resolve_provider_config"),
 ("function:runner/semantic_dispatch.py:invoke_agent", "function:runner/paths.py:resolve_repo_path"),
 ("function:runner/transport/config.py:build_openai_backend", "class:runner/transport/openai_compatible.py:OpenAICompatBackend"),
 ("function:runner/transport/config.py:build_converse_backend", "class:runner/transport/bedrock_converse.py:BedrockConverseBackend"),
 ("class:runner/transport/openai_compatible.py:OpenAICompatBackend", "function:runner/transport/errors.py:normalize_http_error"),
 ("function:runner/transport/tool_loop.py:run_tool_loop", "class:runner/transport/tool_executor.py:ToolExecutor"),
]
for s, t in CALLS:
    edges.append({"source": s, "target": t, "type": "calls", "direction": "forward", "weight": 0.8})

DEPENDS = [
 ("class:runner/transport/bedrock_converse.py:BedrockConverseBackend", "class:runner/transport/errors.py:ErrorCategory"),
 ("function:runner/transport/config.py:resolve_provider_config", "class:runner/transport/capabilities.py:ProviderCapabilities"),
]
for s, t in DEPENDS:
    edges.append({"source": s, "target": t, "type": "depends_on", "direction": "forward", "weight": 0.6})

# ---------------------------------------------------------------- partition
files_sorted = sorted(f["path"] for f in META["files"])
PARTS = 3
chunk = int(math.ceil(len(files_sorted) / float(PARTS)))
groups = [files_sorted[i*chunk:(i+1)*chunk] for i in range(PARTS)]

by_id = {n["id"]: n for n in nodes}
assert len(by_id) == len(nodes), "duplicate node ids"
for e in edges:
    assert e["source"] != e["target"], e

written = []
tot_n = tot_e = 0
for k, grp in enumerate(groups, start=1):
    gset = set(grp)
    pnodes = [n for n in nodes if n["filePath"] in gset]
    pids = set(n["id"] for n in pnodes)
    pedges = [e for e in edges if e["source"] in pids]
    path = os.path.join(OUT, "batch-5-part-%d.json" % k)
    fh = open(path, "w", encoding="utf-8")
    json.dump({"nodes": pnodes, "edges": pedges}, fh, indent=1, ensure_ascii=False)
    fh.close()
    written.append((path, len(pnodes), len(pedges)))
    tot_n += len(pnodes); tot_e += len(pedges)

print("imports emitted:", imp_total, "expected:", sum(len(v) for v in BID.values()))
for p, a, b in written: print(p, a, b)
print("TOTAL nodes", tot_n, "of", len(nodes), "| edges", tot_e, "of", len(edges))
