from unittest.mock import Mock

import pytest
from graphql import graphql_sync

from ariadne import QueryType, make_executable_schema
from ariadne.format_errors import (
    format_errors,
    format_error,
    get_error_extension,
    get_formatted_context,
    safe_repr,
)


@pytest.fixture
def failing_repr_mock():
    return Mock(__repr__=Mock(side_effect=KeyError("test")), spec=["__repr__"])


@pytest.fixture
def erroring_resolvers(failing_repr_mock):
    query = QueryType()

    @query.field("hello")
    def resolve_hello_with_context_and_attribute_error(*_):
        # pylint: disable=undefined-variable, unused-variable
        test_int = 123
        test_str = "test"
        test_dict = {"test": "dict"}
        test_obj = query
        test_failing_repr = failing_repr_mock
        test_undefined.error()  # trigger attr not found error

    return query


@pytest.fixture
def schema(type_defs, resolvers, erroring_resolvers, subscriptions):
    return make_executable_schema(
        type_defs, [resolvers, erroring_resolvers, subscriptions]
    )


def test_default_formatter_extracts_errors_from_result(schema):
    result = graphql_sync(schema, "{ hello }")
    assert format_errors(result, format_error)


def test_default_formatter_is_not_extending_error_by_default(schema):
    result = graphql_sync(schema, "{ hello }")
    error = format_errors(result, format_error)[0]
    assert not error.get("extensions")


def test_default_formatter_extends_error_with_stacktrace(schema):
    result = graphql_sync(schema, "{ hello }")
    error = format_errors(result, format_error, debug=True)[0]
    assert error["extensions"]["exception"]["stacktrace"]


def test_default_formatter_extends_error_with_context(schema):
    result = graphql_sync(schema, "{ hello }")
    error = format_errors(result, format_error, debug=True)[0]
    assert error["extensions"]["exception"]["context"]


def test_default_formatter_fills_context_with_safe_reprs_of_python_context(
    schema, erroring_resolvers, failing_repr_mock
):
    result = graphql_sync(schema, "{ hello }")
    error = format_errors(result, format_error, debug=True)[0]
    context = error["extensions"]["exception"]["context"]

    assert context["test_int"] == safe_repr(123)
    assert context["test_str"] == safe_repr("test")
    assert context["test_dict"] == safe_repr({"test": "dict"})
    assert context["test_failing_repr"] == safe_repr(failing_repr_mock)
    assert context["test_obj"] == safe_repr(erroring_resolvers)


def test_default_formatter_is_not_extending_plain_graphql_error(schema):
    result = graphql_sync(schema, "{ error }")
    error = format_errors(result, format_error, debug=True)[0]
    assert error["extensions"]["exception"] is None


def test_error_extension_is_not_available_for_error_without_traceback():
    error = Mock(__traceback__=None, spec=["__traceback__"])
    assert get_error_extension(error) is None


def test_incomplete_traceback_is_handled_by_context_extractor():
    error = Mock(__traceback__=None, spec=["__traceback__"])
    assert get_formatted_context(error) is None


def test_safe_repr_handles_exception_during_repr(failing_repr_mock):
    assert safe_repr(failing_repr_mock)


def test_safe_repr_includes_exception_type_in_repr(failing_repr_mock):
    assert "KeyError" in safe_repr(failing_repr_mock)
