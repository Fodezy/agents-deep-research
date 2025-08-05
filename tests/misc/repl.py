import inspect
import sys

print("PYTHONPATH:", sys.path)
try:
    import agents
    import agents.run as run_mod
except ModuleNotFoundError:
    print("ERROR: could not import 'agents' or 'agents.run'. Is the venv activated and dependencies installed?")
    sys.exit(1)

print("agents module location:", agents.__file__)
print("run module location:", run_mod.__file__)

# Show what's in run_mod
print("\n--- Public attributes in agents.run ---")
print([n for n in dir(run_mod) if not n.startswith("_")])

# Get RunImpl class
RunImpl = getattr(run_mod, "RunImpl", None)
if RunImpl is None:
    print("ERROR: RunImpl not found in agents.run. Available names:", [n for n in dir(run_mod) if "Run" in n or "Impl" in n])
    sys.exit(1)

print("\n--- Methods on RunImpl ---")
methods = [m for m in dir(RunImpl) if not m.startswith("_")]
print(methods)

# Dump first part of its source (could be large)
try:
    src = inspect.getsource(RunImpl)
    print("\n=== First 400 lines of RunImpl ===")
    print("\n".join(src.splitlines()[:400]))
except Exception as e:
    print("Could not get full RunImpl source:", e)

# Try to surface likely internal helpers for function-call/tool dispatch
candidates = [
    "_get_single_step_result_from_response",
    "_run_single_turn",
    "_run_single_turn_streamed",
    "process_model_response",
    "execute_tools_and_side_effects",
]
for name in candidates:
    if hasattr(RunImpl, name):
        func = getattr(RunImpl, name)
        print(f"\n=== Source for RunImpl.{name} ===")
        try:
            print(inspect.getsource(func))
        except Exception as e:
            print(f"Failed to get source for {name}: {e}")
    else:
        print(f"\n[INFO] RunImpl has no attribute '{name}'")
