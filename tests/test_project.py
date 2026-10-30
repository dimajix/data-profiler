"""Tests of projects: their configuration read, their environments resolved, refused where wrong."""

from pathlib import Path

import pytest

from data_profiler.project import Environment, Project, ProjectError

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm"

_CONFIGURATION = """\
format: 1
tables: cust.*
environments:
  dev:
    url: trino://profiler@dev:8443/crm/sales
    password: ${DEV_PASSWORD}
  prod:
    url: ${PROD_URL}
    password: ${PROD_PASSWORD}
"""


def _project(tmp_path: Path, configuration: str = _CONFIGURATION, **variables: str) -> Project:
    """The project in `tmp_path` of `configuration`, its values taken from `variables`."""
    (tmp_path / "project.yml").write_text(configuration, encoding="utf-8")
    return Project.read(tmp_path, variables)


def test_the_tables_of_a_project_are_matched_by_its_regular_expression(tmp_path: Path) -> None:
    tables = _project(tmp_path).tables
    assert tables.fullmatch("cust_addr")
    assert not tables.fullmatch("ord")


def test_the_tables_of_a_project_are_matched_by_its_list_of_names(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("tables: cust.*", "tables: [cust, ord.itm]")
    tables = _project(tmp_path, configuration).tables
    assert tables.fullmatch("cust")
    assert tables.fullmatch("ord.itm")
    assert not tables.fullmatch("ord_itm"), "a name is matched as it is written"
    assert not tables.fullmatch("cust_addr")


def test_an_environment_is_resolved_from_the_variables_it_names(tmp_path: Path) -> None:
    project = _project(tmp_path, DEV_PASSWORD="secret")  # those of prod are not needed
    assert project.environment("dev") == Environment(
        name="dev",
        url="trino://profiler@dev:8443/crm/sales",
        directory=tmp_path / "dev",
        password="secret",
    )


def test_the_url_of_an_environment_may_be_a_variable(tmp_path: Path) -> None:
    url = "trino://profiler@prod:8443/crm/sales"
    project = _project(tmp_path, PROD_URL=url, PROD_PASSWORD="secret")
    assert project.environment("prod").url == url


def test_an_environment_keeps_its_results_in_its_directory(tmp_path: Path) -> None:
    environment = _project(tmp_path, DEV_PASSWORD="secret").environment("dev")
    assert environment.profile == tmp_path / "dev" / "profile.yml"
    assert environment.workspace == tmp_path / "dev" / "workspace"


def test_the_password_of_an_environment_is_not_shown(tmp_path: Path) -> None:
    environment = _project(tmp_path, DEV_PASSWORD="secret").environment("dev")
    assert "secret" not in repr(environment)


def test_an_environment_whose_variable_is_not_set_is_refused_naming_it(tmp_path: Path) -> None:
    project = _project(tmp_path, PROD_URL="trino://profiler@prod:8443/crm/sales")
    problem = (
        r"project\.yml: the password of the environment prod is the variable PROD_PASSWORD, which"
        r" neither the process sets nor .*\.env$"
    )
    with pytest.raises(ProjectError, match=problem):
        project.environment("prod")


def test_the_variables_are_completed_by_those_of_the_project(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("# The password of dev\nDEV_PASSWORD=secret\n", encoding="utf-8")
    assert _project(tmp_path).environment("dev").password == "secret"


def test_a_variable_given_is_not_overridden_by_the_project(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DEV_PASSWORD=secret\n", encoding="utf-8")
    assert _project(tmp_path, DEV_PASSWORD="given").environment("dev").password == "given"


def test_variables_of_the_project_that_are_no_text_are_refused(tmp_path: Path) -> None:
    (tmp_path / ".env").write_bytes(b"DEV_PASSWORD=\xff\xfe\n")
    with pytest.raises(ProjectError, match=r"\.env is no text in UTF-8$"):
        _project(tmp_path)


def test_an_environment_the_project_does_not_have_is_refused_naming_those_it_has(
    tmp_path: Path,
) -> None:
    with pytest.raises(ProjectError, match="has no environment test; it has: dev, prod"):
        _project(tmp_path).environment("test")


def test_a_password_written_out_is_refused_without_showing_it(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("${DEV_PASSWORD}", "secret")
    with pytest.raises(ProjectError, match="environment dev gives its password other") as error:
        _project(tmp_path, configuration)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("name", ["Dev", "../dev", ".dev", "dev/old", "dev env", "-dev", "_dev"])
def test_an_environment_that_is_no_name_of_a_directory_is_refused(
    tmp_path: Path, name: str
) -> None:
    configuration = _CONFIGURATION.replace("  dev:", f"  {name!r}:")
    with pytest.raises(ProjectError, match="is named other than in lower case letters"):
        _project(tmp_path, configuration)


def test_a_url_with_a_variable_in_it_is_refused(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("profiler@dev", "${USER}@dev")
    with pytest.raises(ProjectError, match="environment dev gives its url with a variable in it"):
        _project(tmp_path, configuration)


def test_a_password_with_a_variable_in_it_is_refused(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("${DEV_PASSWORD}", "x${DEV_PASSWORD}")
    with pytest.raises(ProjectError, match="environment dev gives its password other"):
        _project(tmp_path, configuration)


def test_tables_that_are_no_regular_expression_are_refused(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("tables: cust.*", "tables: cust(")
    with pytest.raises(ProjectError, match="tables is no regular expression"):
        _project(tmp_path, configuration)


def test_a_configuration_that_is_no_document_of_a_project_is_refused(tmp_path: Path) -> None:
    configuration = _CONFIGURATION.replace("format: 1", "format: 2")
    with pytest.raises(ProjectError, match=r"project\.yml is of format 2"):
        _project(tmp_path, configuration)


def test_a_directory_without_a_configuration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match=r"project\.yml cannot be read"):
        Project.read(tmp_path, {})


def test_the_example_project_profiles_the_simulation_environment() -> None:
    project = Project.read(_EXAMPLE, {"SIMULATION_PASSWORD": "profiler"})
    environment = project.environment("simulation")
    assert environment.url == "trino://profiler@localhost:8443/crm/sales"
    assert environment.directory == _EXAMPLE / "simulation"
    assert project.tables.fullmatch("cust_addr")
