import pytest
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.urls import reverse
from tests.factories import ClientFactory, SalesRepFactory, AttributeFactory

from ..admin import AdvancedListFilters
from ..models import AdvancedFilter
from .factories import AdvancedFilterFactory


URL_NAME_CLIENT_CHANGELIST = "admin:customers_client_changelist"


@pytest.fixture
def user(db):
    user = SalesRepFactory()
    user.user_permissions.add(Permission.objects.get(codename="change_client"))
    return user


@pytest.fixture()
def client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def advanced_filter(user):
    af = AdvancedFilterFactory.build(
        title="Russian speakers", url="foo", model="customers.Client", created_by=user
    )
    af.query = Q(language="ru")
    af.save()
    return af


@pytest.fixture
def advanced_filter_m2m(user):
    af = AdvancedFilterFactory.build(
        title="M2M test", url="foo", model="customers.Client", created_by=user
    )
    af.query = Q(attributes__name__contains="1") & Q(attributes__name__contains="2")
    af.save()
    return af


@pytest.fixture(autouse=True)
def clients(user):
    AttributeFactory.create_batch(3)
    ClientFactory.create_batch(8, attributes=('1', '2', '3'), assigned_to=user, language="en")
    ClientFactory.create_batch(2, assigned_to=user, language="ru")


def test_filters_not_available(client, advanced_filter):
    url = reverse(URL_NAME_CLIENT_CHANGELIST)
    res = client.get(url, data={"_afilter": advanced_filter.pk})
    assert res.status_code == 200
    cl = res.context_data["cl"]
    assert not any(isinstance(f, AdvancedListFilters) for f in cl.filter_specs)
    # filter not applied due to user not being in list
    if hasattr(cl, "queryset"):
        assert cl.queryset.count() == 10


def test_filters_available_to_users(client, user, advanced_filter):
    advanced_filter.users.add(user)
    url = reverse(URL_NAME_CLIENT_CHANGELIST)
    res = client.get(url, data={"_afilter": advanced_filter.pk})
    assert res.status_code == 200
    cl = res.context_data["cl"]
    assert any(isinstance(f, AdvancedListFilters) for f in cl.filter_specs)
    if hasattr(cl, "queryset"):
        assert cl.queryset.count() == 2


def test_filters_available_to_groups(client, user, advanced_filter):
    group = user.groups.create()
    advanced_filter.groups.add(group)
    url = reverse(URL_NAME_CLIENT_CHANGELIST)
    res = client.get(url, data={"_afilter": advanced_filter.pk})
    assert res.status_code == 200
    cl = res.context_data["cl"]
    assert cl.filter_specs
    if hasattr(cl, "queryset"):
        assert cl.queryset.count() == 2


def test_many_to_many_filters(client, user, advanced_filter_m2m):
    group = user.groups.create()
    advanced_filter_m2m.groups.add(group)
    url = reverse(URL_NAME_CLIENT_CHANGELIST)
    res = client.get(url, data={"_afilter": advanced_filter_m2m.pk})
    assert res.status_code == 200
    cl = res.context_data["cl"]
    assert cl.filter_specs
    if hasattr(cl, "queryset"):
        assert cl.queryset.count() == 8
