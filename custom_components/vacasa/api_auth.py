"""Authentication methods for the Vacasa API client."""
import asyncio
import json
import logging
import re
import time
from typing import Optional

from .const import AUTH_URL, DEFAULT_TIMEOUT, MAX_RETRIES, RETRY_DELAY

_LOGGER = logging.getLogger(__name__)


async def authenticate(self) -> str:
    """Authenticate with Vacasa and get a token.

    This method implements the authentication flow without using Selenium,
    by making direct HTTP requests to simulate the browser-based auth flow.

    Returns:
        The authentication token

    Raises:
        AuthenticationError: If authentication fails
    """
    from .api_client import AuthenticationError

    session = await self.ensure_session()

    # Implement retry logic
    retry_count = 0
    last_error = None

    while retry_count < MAX_RETRIES:
        try:
            if retry_count > 0:
                # Wait before retrying
                wait_time = RETRY_DELAY * (2 ** (retry_count - 1))  # Exponential backoff
                _LOGGER.debug(
                    "Retrying authentication (attempt %s/%s) after %ss",
                    retry_count + 1,
                    MAX_RETRIES,
                    wait_time,
                )
                await asyncio.sleep(wait_time)

            # Step 1: Get the login page to obtain CSRF token
            _LOGGER.debug("Fetching login page (attempt %s/%s)", retry_count + 1, MAX_RETRIES)

            # Try with response_type=token to avoid unsupported_response_type error
            auth_params = {
                "next": "/authorize",
                "directory_hint": "email",
                "owner_migration_needed": "true",
                "client_id": self._client_id,
                "response_type": "token",  # Use token instead of token,id_token
                "redirect_uri": "https://owners.vacasa.com",
                "scope": "owners:read employees:read",
                "audience": "owner.vacasa.io",
                "state": f"{int(time.time())}",  # Use timestamp as state
                "nonce": f"{int(time.time())}-nonce",  # Use timestamp as nonce
                "mode": "owner",
            }

            _LOGGER.debug(
                "Auth URL with params: %s?%s",
                AUTH_URL,
                "&".join([f"{k}={v}" for k, v in auth_params.items()]),
            )

            async with session.get(
                AUTH_URL, params=auth_params, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(
                        "Failed to load login page: %s - Response: %s...",
                        response.status,
                        response_text[:200],
                    )
                    raise AuthenticationError(f"Failed to load login page: {response.status}")

                login_page = await response.text()

                # Extract CSRF token from the login page
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page)
                if not csrf_match:
                    _LOGGER.error(
                        "Could not find CSRF token on login page. Page snippet: %s...",
                        login_page[:200],
                    )
                    raise AuthenticationError("Could not find CSRF token on login page")

                csrf_token = csrf_match.group(1)
                _LOGGER.debug("Found CSRF token: %s...", csrf_token[:10])

            # Step 2: Submit login credentials
            _LOGGER.debug("Submitting login credentials")
            login_data = {
                "csrfmiddlewaretoken": csrf_token,
                "username": self._username,
                "password": self._password,
                "next": (
                    f"/authorize?directory_hint=email&owner_migration_needed=true"
                    f"&client_id={self._client_id}&response_type=token"
                    f"&redirect_uri=https://owners.vacasa.com"
                    f"&scope=owners:read%20employees:read&audience=owner.vacasa.io"
                    f"&state={auth_params['state']}&nonce={auth_params['nonce']}&mode=owner"
                ),
            }

            headers = {
                "Referer": f"{AUTH_URL}?{self._format_params(auth_params)}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            async with session.post(
                AUTH_URL,
                data=login_data,
                headers=headers,
                allow_redirects=False,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                # Check for redirect (successful login)
                if response.status not in (302, 303):
                    _LOGGER.error(
                        "Login failed with status %s. Expected redirect (302/303).",
                        response.status,
                    )
                    raise AuthenticationError(f"Login failed with status {response.status}")

                # Get redirect location
                redirect_url = response.headers.get("Location")
                if not redirect_url:
                    _LOGGER.error("No redirect URL after login")
                    raise AuthenticationError("No redirect URL after login")

                _LOGGER.debug("Login successful, redirecting to: %s", redirect_url)

            # Step 3: Follow redirects until we get the token
            _LOGGER.debug("Following auth redirects")
            token = await self._follow_auth_redirects(redirect_url)

            if not token:
                _LOGGER.error("Failed to obtain token after authentication")
                raise AuthenticationError("Failed to obtain token after authentication")

            self._token = token
            _LOGGER.debug("Successfully obtained token: %s...", token[:30])

            # Extract token expiry from JWT
            try:
                # JWT tokens have 3 parts separated by dots
                token_parts = token.split(".")
                if len(token_parts) >= 2:
                    # Decode the payload (middle part)
                    padded_payload = token_parts[1] + "=" * (4 - len(token_parts[1]) % 4)
                    payload = json.loads(self._base64_url_decode(padded_payload))

                    # Extract expiry timestamp
                    if "exp" in payload:
                        self._token_expiry = self._timestamp_to_datetime(payload["exp"])
                        _LOGGER.debug("Token expires at %s", self._token_expiry)
                    else:
                        _LOGGER.warning("No expiry found in token payload")
            except Exception as e:
                _LOGGER.warning("Failed to parse JWT token: %s", e)

            return self._token

        except Exception as e:
            last_error = e
            _LOGGER.warning(
                "Authentication attempt %s/%s failed: %s",
                retry_count + 1,
                MAX_RETRIES,
                e,
            )
            retry_count += 1

    # If we've exhausted all retries, raise the last error
    _LOGGER.error("Authentication failed after %s attempts: %s", MAX_RETRIES, last_error)
    raise AuthenticationError(f"Authentication failed after {MAX_RETRIES} attempts: {last_error}")


async def _follow_auth_redirects(self, initial_url: str) -> Optional[str]:
    """Follow authentication redirects to extract the token.

    Args:
        initial_url: The initial redirect URL

    Returns:
        The authentication token if found, None otherwise
    """
    session = await self.ensure_session()
    current_url = initial_url
    max_redirects = 10
    redirect_count = 0

    _LOGGER.debug("Following auth redirects starting with: %s", current_url)

    while redirect_count < max_redirects:
        redirect_count += 1

        # Check if the URL already contains the token
        if "#access_token=" in current_url:
            match = re.search(r"access_token=([^&]+)", current_url)
            if match:
                token = match.group(1)
                _LOGGER.debug("Extracted token from URL fragment")
                return token

        # If URL is relative, make it absolute
        if current_url.startswith("/"):
            current_url = f"https://accounts.vacasa.io{current_url}"

        # Follow the redirect
        try:
            async with session.get(
                current_url, allow_redirects=False, timeout=DEFAULT_TIMEOUT
            ) as response:
                if response.status in (301, 302, 303, 307, 308):
                    # Handle redirect
                    current_url = response.headers.get("Location", "")
                    if not current_url:
                        _LOGGER.warning("No Location header in redirect response")
                        return None
                else:
                    # Check for token in URL
                    if "#" in str(response.url):
                        fragment = str(response.url).split("#")[1]
                        match = re.search(r"access_token=([^&]+)", fragment)
                        if match:
                            token = match.group(1)
                            _LOGGER.debug("Extracted token from response URL fragment")
                            return token

                    # If we've reached owners.vacasa.com without a token, try one more request
                    if "owners.vacasa.com" in str(response.url.host):
                        page_content = await response.text()
                        token_match = re.search(r'access_token=([^&"\']+)', page_content)
                        if token_match:
                            token = token_match.group(1)
                            _LOGGER.debug("Found token in page content")
                            return token
                    
                    _LOGGER.warning("No token found in redirect chain")
                    return None
        except Exception as e:
            _LOGGER.error("Error following redirect: %s", e)
            return None

    _LOGGER.warning("Exceeded maximum redirects without finding token")
    return None


# The _try_calendar_page method has been removed as it was a last-resort fallback
# that is no longer needed with the simplified authentication flow.
