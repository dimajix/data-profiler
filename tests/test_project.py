"""Tests of projects: their configuration read, their environments resolved, refused where wrong."""

from pathlib import Path

import pytest

from data_profiler.detect import SemanticType
from data_profiler.project import Project, ProjectError

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm"

_CONFIGURATION = """\
format: 3
tables: cust.*
environments:
  dev:
    url: trino://dev:8443/crm/sales
    user: profiler
    password: ${DEV_PASSWORD}
  prod:
    url: ${PROD_URL}
    user: ${PROD_USER}
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


_TYPES = """\
types:
  {name}:
    pattern: "{pattern}"
    sensitivity: personal
"""


def test_the_semantic_types_of_a_project_are_read_with_their_patterns(
    tmp_path: Path, account_number: SemanticType
) -> None:
    configuration = _CONFIGURATION + _TYPES.format(name="account-number", pattern="A[0-9]{10}")
    assert _project(tmp_path, configuration).types == (account_number,)


def test_a_project_without_semantic_types_of_its_own_has_none(tmp_path: Path) -> None:
    assert _project(tmp_path).types == ()


def test_a_semantic_type_of_a_project_that_cannot_be_is_refused_naming_it(tmp_path: Path) -> None:
    configuration = _CONFIGURATION + _TYPES.format(name="email", pattern="A[0-9]{10}")
    with pytest.raises(ProjectError, match=r"project\.yml: types: email is a semantic type of the"):
        _project(tmp_path, configuration)


def test_a_semantic_type_of_a_project_without_its_sensitivity_is_refused(tmp_path: Path) -> None:
    configuration = _CONFIGURATION + "types:\n  account:\n    pattern: A[0-9]\n"
    with pytest.raises(ProjectError, match=r"types\.account\.sensitivity: .*required"):
        _project(tmp_path, configuration)


def test_an_environment_is_resolved_from_the_variables_it_names(tmp_path: Path) -> None:
    environment = _project(tmp_path, DEV_PASSWORD="secret").environment("dev")
    assert environment.name == "dev"
    assert environment.url == "trino://dev:8443/crm/sales"
    assert environment.user == "profiler"
    assert environment.directory == tmp_path / "dev"
    assert environment.password == "secret", "those of prod are not needed"


def test_an_environment_needs_its_variables_only_when_they_are_asked_for(tmp_path: Path) -> None:
    environment = _project(tmp_path).environment("prod")
    assert environment.report == tmp_path / "prod" / "report.html"
    with pytest.raises(ProjectError, match="the url of the environment prod is the variable"):
        assert environment.url


def test_the_url_and_the_user_of_an_environment_may_be_variables(tmp_path: Path) -> None:
    url = "trino://prod:8443/crm/sales"
    project = _project(tmp_path, PROD_URL=url, PROD_USER="kaya@dimajix.de")
    environment = project.environment("prod")
    assert environment.url == url
    assert environment.user == "kaya@dimajix.de", "the user is taken as written"


def test_the_overrides_of_a_project_are_in_its_directory(tmp_path: Path) -> None:
    assert _project(tmp_path).overrides == tmp_path / "overrides.yml"


def test_an_environment_keeps_its_results_in_its_directory(tmp_path: Path) -> None:
    environment = _project(tmp_path, DEV_PASSWORD="secret").environment("dev")
    assert environment.profile == tmp_path / "dev" / "profile"
    assert environment.workspace == tmp_path / "dev" / "workspace"
    assert environment.report == tmp_path / "dev" / "report.html"


def test_the_password_of_an_environment_is_not_shown(tmp_path: Path) -> None:
    environment = _project(tmp_path, DEV_PASSWORD="secret").environment("dev")
    assert "secret" not in repr(environment)


def test_an_environment_whose_variable_is_not_set_is_refused_naming_it(tmp_path: Path) -> None:
    project = _project(tmp_path, PROD_URL="trino://prod:8443/crm/sales")
    problem = (
        r"project\.yml: the user of the environment prod is the variable PROD_USER, which"
        r" neither the process sets nor .*\.env$"
    )
    with pytest.raises(ProjectError, match=problem):
        assert project.environment("prod").user


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


@pytest.mark.parametrize(
    ("value", "written", "setting"),
    [
        ("trino://dev:8443", "trino://${HOST}:8443", "url"),
        ("user: profiler", "user: ${USER}@dimajix.de", "user"),
    ],
)
def test_a_url_or_a_user_with_a_variable_in_it_is_refused(
    tmp_path: Path, value: str, written: str, setting: str
) -> None:
    configuration = _CONFIGURATION.replace(value, written)
    with pytest.raises(ProjectError, match=f"environment dev gives its {setting} with a variable"):
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
    configuration = _CONFIGURATION.replace("format: 3", "format: 2")
    with pytest.raises(ProjectError, match=r"project\.yml is of format 2"):
        _project(tmp_path, configuration)


def test_a_directory_without_a_configuration_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match=r"project\.yml cannot be read"):
        Project.read(tmp_path, {})


def test_the_example_project_profiles_the_simulation_environment() -> None:
    project = Project.read(_EXAMPLE, {"SIMULATION_PASSWORD": "profiler"})
    environment = project.environment("simulation")
    assert environment.url == "trino://localhost:8443/crm/sales"
    assert environment.user == "profiler"
    assert environment.directory == _EXAMPLE / "simulation"
    assert project.tables.fullmatch("cust_addr")
