# NeoscopeBuddy — Test Design

## Test-to-Source Coverage Map

Every test file and which source modules it exercises. Green nodes are source modules; orange are test files.

```mermaid
graph LR
    subgraph "source modules"
        application
        profile_manager
        config_manager
        config_result
        command_executor
        argument_processor
        environment_helper
        system_detector
        path_helper
        gamescope_args
        types
        exceptions
    end

    subgraph "test files"
        t_app["test_application"]
        t_prof["test_profile_manager"]
        t_cfg["test_config_manager"]
        t_cmd["test_command_executor"]
        t_arg["test_argument_processor"]
        t_env["test_environment_helper"]
        t_sys["test_system_detector"]
        t_ga["test_gamescope_args"]
        t_cr["test_config_result"]
        t_types["test_types"]
        t_exc["test_exceptions"]
    end

    t_app --> application
    t_app --> config_result
    t_app --> exceptions

    t_prof --> profile_manager
    t_prof --> config_manager

    t_cfg --> config_manager
    t_cfg --> config_result
    t_cfg --> profile_manager

    t_cmd --> command_executor
    t_cmd --> system_detector

    t_arg --> argument_processor
    t_arg --> profile_manager

    t_env --> environment_helper
    t_env --> command_executor
    t_env --> system_detector

    t_sys --> system_detector

    t_ga --> gamescope_args
    t_ga --> argument_processor
    t_ga --> profile_manager

    t_cr --> config_result
    t_cr --> config_manager

    t_types --> types
    t_types --> argument_processor
    t_types --> profile_manager

    t_exc --> exceptions
    t_exc --> config_manager
    t_exc --> profile_manager

    style application fill:#9f9,stroke:#6b6
    style profile_manager fill:#9f9,stroke:#6b6
    style config_manager fill:#9f9,stroke:#6b6
    style config_result fill:#9f9,stroke:#6b6
    style command_executor fill:#9f9,stroke:#6b6
    style argument_processor fill:#9f9,stroke:#6b6
    style environment_helper fill:#9f9,stroke:#6b6
    style system_detector fill:#9f9,stroke:#6b6
    style path_helper fill:#9f9,stroke:#6b6
    style gamescope_args fill:#9f9,stroke:#6b6
    style types fill:#9f9,stroke:#6b6
    style exceptions fill:#9f9,stroke:#6b6
```

### Source Module Test Coverage

| Source Module | Tested by |
|---|---|
| `application.py` | test_application, test_types, test_path_helper, test_config_manager, test_config_result, test_exceptions, test_system_detector, test_environment_helper, test_gamescope_args, test_argument_processor |
| `profile_manager.py` | test_profile_manager, test_types, test_config_manager, test_exceptions, test_gamescope_args, test_argument_processor |
| `config_manager.py` | test_config_manager, test_config_result, test_path_helper, test_exceptions |
| `command_executor.py` | test_command_executor, test_environment_helper |
| `argument_processor.py` | test_argument_processor, test_types, test_gamescope_args |
| `environment_helper.py` | test_environment_helper |
| `system_detector.py` | test_system_detector, test_command_executor, test_environment_helper, test_path_helper |
| `config_result.py` | test_config_result, test_application |
| `path_helper.py` | test_path_helper |
| `gamescope_args.py` | test_gamescope_args |
| `types.py` | test_types |
| `exceptions.py` | test_exceptions |

## Fixture Mock Target Map

Which conftest.py fixtures patch which source methods. This shows the mock boundary between tests and production code.

```mermaid
graph LR
    subgraph "conftest.py fixtures"
        f_int["mock_integration_setup"]
        f_gsc["mock_gamescope"]
        f_cfg["mock_config_file"]
        f_sys_det["mock_system_detection_scenarios"]
        f_isgsm["mock_is_gamescope_active"]
        f_env["mock_env_commands"]
        f_wf["mock_application_workflow"]
        f_sys_comp["system_detection_comprehensive"]
        f_int_setup["integration_test_setup"]
    end

    subgraph "source methods"
        sm_rnb["CommandExecutor.run_nonblocking"]
        sm_bc["CommandExecutor.build_command"]
        sm_gec["CommandExecutor.get_env_commands"]
        sm_fe["SystemDetector.find_executable"]
        sm_iga["SystemDetector.is_gamescope_active"]
        sm_ffc["ConfigManager.find_config_file"]
        sm_lc["ConfigManager.load_config"]
        sm_ma["ProfileManager.merge_arguments"]
    end

    f_int --> sm_rnb
    f_int --> sm_bc
    f_int --> sm_ma
    f_int --> sm_lc

    f_gsc --> sm_fe

    f_cfg --> sm_ffc

    f_sys_det --> sm_iga
    f_sys_det --> sm_fe

    f_isgsm --> sm_iga

    f_env --> sm_gec

    f_wf --> sm_fe
    f_wf --> sm_iga
    f_wf --> sm_rnb
    f_wf --> sm_bc
    f_wf --> sm_ffc

    f_sys_comp --> sm_iga
    f_sys_comp --> sm_fe

    f_int_setup --> sm_ffc
    f_int_setup --> sm_lc
    f_int_setup --> sm_iga
    f_int_setup --> sm_fe
    f_int_setup --> sm_rnb
    f_int_setup --> sm_bc
    f_int_setup --> sm_ma

    style sm_rnb fill:#f96,stroke:#c66
    style sm_bc fill:#f96,stroke:#c66
    style sm_gec fill:#f96,stroke:#c66
    style sm_fe fill:#f96,stroke:#c66
    style sm_iga fill:#f96,stroke:#c66
    style sm_ffc fill:#f96,stroke:#c66
    style sm_lc fill:#f96,stroke:#c66
    style sm_ma fill:#f96,stroke:#c66
```

### Fixture Quick Reference

| Fixture | Type | Mock targets |
|---|---|---|
| `mock_system_exit` | patch | `sys.exit` |
| `mock_integration_setup` | dict | `run_nonblocking`, `build_command`, `print`, `merge_arguments`, `load_config` |
| `temp_config_file` | tempdir | none |
| `temp_config_with_content` | factory | none |
| `mock_gamescope` | patch | `find_executable` → True |
| `mock_config_file` | factory | `find_config_file` |
| `mock_system_detection_scenarios` | dict | `is_gamescope_active`, `find_executable` |
| `mock_is_gamescope_active` | patch | `is_gamescope_active` |
| `mock_env_commands` | factory | `get_env_commands` |
| `mock_ld_preload_scenarios` | monkeypatch | `LD_PRELOAD`, `NSCB_DISABLE_LD_PRELOAD_WRAP`, `FAUGUS_LOG` |
| `mock_application_workflow` | class | `find_executable`, `is_gamescope_active`, `run_nonblocking`, `build_command`, `find_config_file` |
| `xdg_config_scenarios` | monkeypatch | `XDG_CONFIG_HOME`, `HOME` |
| `system_detection_comprehensive` | class | `is_gamescope_active`, `find_executable` |
| `integration_test_setup` | class | `find_config_file`, `load_config`, `is_gamescope_active`, `find_executable`, `run_nonblocking`, `build_command`, `merge_arguments` |

Data-only fixtures (no mocking): `mock_execution_scenarios`, `mock_environment_variables`, `complex_args_scenario`, `profile_scenarios`, `config_scenarios`, `error_simulation`, `test_config_content`, `argument_processing_patterns`, `error_simulation_comprehensive`, `profile_test_scenarios`.

## Test Module → Source Method Map

What each test file actually tests at the method level.

```mermaid
graph TD
    subgraph "test_application.py"
        ta_run["Application.run"]
        ta_proc["Application._process_profiles"]
        ta_help["print_help"]
        ta_main["main"]
    end

    subgraph "test_profile_manager.py"
        tp_parse["parse_profile_args"]
        tp_merge["merge_arguments"]
        tp_multi["merge_multiple_profiles"]
        tp_merge_flags["_merge_flags"]
    end

    subgraph "test_config_manager.py"
        tc_find["find_config_file"]
        tc_load["load_config"]
        tc_sections["section parsing"]
    end

    subgraph "test_command_executor.py"
        te_build["build_command"]
        te_exec["execute_gamescope_command"]
        te_ld["LD_PRELOAD handling"]
    end

    subgraph "test_argument_processor.py"
        ta_split["split_at_separator"]
        ta_sep["separate_flags_and_positionals"]
    end

    subgraph "test_environment_helper.py"
        ten_prepost["get_pre_post_commands"]
        ten_active["is_gamescope_active"]
        ten_ld["should_disable_ld_preload_wrap"]
        ten_debug["debug_log"]
    end

    style ta_run fill:#ff9,stroke:#cc6
    style ta_proc fill:#ff9,stroke:#cc6
    style ta_help fill:#ff9,stroke:#cc6
    style ta_main fill:#ff9,stroke:#cc6
    style tp_parse fill:#ff9,stroke:#cc6
    style tp_merge fill:#ff9,stroke:#cc6
    style tp_multi fill:#ff9,stroke:#cc6
    style tp_merge_flags fill:#ff9,stroke:#cc6
    style tc_find fill:#ff9,stroke:#cc6
    style tc_load fill:#ff9,stroke:#cc6
    style tc_sections fill:#ff9,stroke:#cc6
    style te_build fill:#ff9,stroke:#cc6
    style te_exec fill:#ff9,stroke:#cc6
    style te_ld fill:#ff9,stroke:#cc6
    style ta_split fill:#ff9,stroke:#cc6
    style ta_sep fill:#ff9,stroke:#cc6
    style ten_prepost fill:#ff9,stroke:#cc6
    style ten_active fill:#ff9,stroke:#cc6
    style ten_ld fill:#ff9,stroke:#cc6
    style ten_debug fill:#ff9,stroke:#cc6
```

## Test Strategy

- **`@pytest.mark.unit`** — isolated function behavior, heavy mocking
- **`@pytest.mark.integration`** — cross-module workflows with mocked I/O
- **`@pytest.mark.e2e`** — full application flow from args to execution

Run: `make test` (`uv run pytest --tb=short --cov=src --cov-report=term-missing --cov-branch`).

## Testing Patterns

- **AAA**: Arrange → Act → Assert
- **Mock paths**: always at class method level (e.g., `nscb.command_executor.CommandExecutor.run_nonblocking`)
- **Temp files**: `tempfile.mkdtemp()` for realistic config I/O
- **Parameterized**: conflict resolution, config parsing, error scenarios
- **Substring-safe**: regex assertions prevent `-f` matching `--framerate-limit`
