# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest

from unittest.mock import patch, Mock
from taiga_contrib_gitlab_auth import connector as gitlab


def test_url_builder():
    with patch("taiga_contrib_gitlab_auth.connector.URL", "http://localhost:4321"):
        assert (gitlab._build_url("login", "authorize") ==
                "http://localhost:4321/oauth/authorize")
        assert (gitlab._build_url("login", "access-token") ==
                "http://localhost:4321/oauth/token")
        assert (gitlab._build_url("user", "profile") ==
                "http://localhost:4321/api/v4/user")


def test_login_without_settings_params():
    with pytest.raises(gitlab.GitLabApiError) as e, \
            patch("taiga_contrib_gitlab_auth.connector.requests") as m_requests:
        m_requests.post.return_value = m_response = Mock()
        m_response.status_code = 200
        m_response.json.return_value = {"access_token": "xxxxxxxx"}

        auth_info = gitlab.login("*access-code*", "**client-id**", "*ient-secret*", gitlab.HEADERS)
    assert e.value.status_code == 400
    assert "error_message" in e.value.detail


def test_login_success():
    with patch("taiga_contrib_gitlab_auth.connector.requests") as m_requests, \
            patch("taiga_contrib_gitlab_auth.connector.URL", "http://localhost:4321"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_ID", "*CLIENT_ID*"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_SECRET", "*CLIENT_SECRET*"):
        m_requests.post.return_value = m_response = Mock()
        m_response.status_code = 200
        m_response.json.return_value = {"access_token": "xxxxxxxx"}

        auth_info = gitlab.login("*access-code*", "http://localhost:1234", "**client-id**", "*client-secret*", gitlab.HEADERS)

        assert auth_info.access_token == "xxxxxxxx"
        m_requests.post.assert_called_once_with("http://localhost:4321/oauth/token",
                                                headers=gitlab.HEADERS,
                                                params={'code': '*access-code*',
                                                        'client_id': '**client-id**',
                                                        'client_secret': '*client-secret*',
                                                        'grant_type': 'authorization_code',
                                                        'redirect_uri': 'http://localhost:1234'})


def test_login_whit_errors():
    with pytest.raises(gitlab.GitLabApiError) as e, \
            patch("taiga_contrib_gitlab_auth.connector.requests") as m_requests, \
            patch("taiga_contrib_gitlab_auth.connector.URL", "http://localhost:4321"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_ID", "*CLIENT_ID*"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_SECRET", "*CLIENT_SECRET*"):
        m_requests.post.return_value = m_response = Mock()
        m_response.status_code = 200
        m_response.json.return_value = {"error": "Invalid credentials"}

        gitlab.login("*access-code*", "**client-id**", "*ient-secret*", gitlab.HEADERS)
    assert e.value.status_code == 400
    assert e.value.detail["status_code"] == 200
    assert e.value.detail["error"] == "Invalid credentials"


def test_get_user_profile_success():
    with patch("taiga_contrib_gitlab_auth.connector.requests") as m_requests, \
            patch("taiga_contrib_gitlab_auth.connector.URL", "http://localhost:4321"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_ID", "*CLIENT_ID*"), \
            patch("taiga_contrib_gitlab_auth.connector.CLIENT_SECRET", "*CLIENT_SECRET*"):
        m_requests.get.return_value = m_response = Mock()
        m_response.status_code = 200
        m_response.json.return_value = {"id": 1955,
                                        "username": "mmcfly",
                                        "name": "martin seamus mcfly",
                                        "bio": "time traveler"}

        user_profile = gitlab.get_user_profile(gitlab.HEADERS)

        assert user_profile.id == 1955
        assert user_profile.username == "mmcfly"
        assert user_profile.full_name == "martin seamus mcfly"
        assert user_profile.bio == "time traveler"
        m_requests.get.assert_called_once_with("http://localhost:4321/api/v4/user",
                                               headers=gitlab.HEADERS)


def test_get_user_profile_whit_errors():
    with pytest.raises(gitlab.GitLabApiError) as e, \
            patch("taiga_contrib_gitlab_auth.connector.requests") as m_requests:
        m_requests.get.return_value = m_response = Mock()
        m_response.status_code = 401
        m_response.json.return_value = {"error": "Invalid credentials"}

        gitlab.get_user_profile(gitlab.HEADERS)
    assert e.value.status_code == 400
    assert e.value.detail["status_code"] == 401
    assert e.value.detail["error"] == "Invalid credentials"


def test_me():
    with patch("taiga_contrib_gitlab_auth.connector.login") as m_login, \
            patch("taiga_contrib_gitlab_auth.connector.get_user_profile") as m_get_user_profile:
        m_login.return_value = gitlab.AuthInfo(access_token="xxxxxxxx")
        m_get_user_profile.return_value = gitlab.User(id=1955,
                                                      username="mmcfly",
                                                      full_name="martin seamus mcfly",
                                                      email="mmcfly@bttf.com",
                                                      bio="time traveler")
        email, user = gitlab.me("**access-code**", "http://localhost:1234")

        assert email == "mmcfly@bttf.com"
        assert user.id == 1955
        assert user.username == "mmcfly"
        assert user.full_name == "martin seamus mcfly"
        assert user.bio == "time traveler"

        headers = gitlab.HEADERS.copy()
        headers["Authorization"] = "Bearer xxxxxxxx"
        m_get_user_profile.assert_called_once_with(headers=headers)
