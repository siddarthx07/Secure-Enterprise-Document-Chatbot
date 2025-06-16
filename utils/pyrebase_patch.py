import sys
import os

# Execute this patch before any pyrebase import
def patch_pyrebase():
    """
    Fixes the Pyrebase4 compatibility issue with newer versions of requests
    by adding a mock module for the removed vendored urllib3 in requests
    """
    # Only apply patch if module doesn't exist
    if 'requests.packages.urllib3.contrib.appengine' not in sys.modules:
        # Create the path to the mock module
        import requests
        requests_path = os.path.dirname(requests.__file__)
        
        # Create mock packages
        if not hasattr(requests, 'packages'):
            requests.packages = type('MockPackages', (), {})()
        
        if not hasattr(requests.packages, 'urllib3'):
            requests.packages.urllib3 = type('MockUrllib3', (), {})()
        
        if not hasattr(requests.packages.urllib3, 'contrib'):
            requests.packages.urllib3.contrib = type('MockContrib', (), {})()
        
        if not hasattr(requests.packages.urllib3.contrib, 'appengine'):
            requests.packages.urllib3.contrib.appengine = type('MockAppEngine', (), {})()
            
        # Define the missing function
        if not hasattr(requests.packages.urllib3.contrib.appengine, 'is_appengine_sandbox'):
            requests.packages.urllib3.contrib.appengine.is_appengine_sandbox = lambda: False
            
        sys.modules['requests.packages'] = requests.packages
        sys.modules['requests.packages.urllib3'] = requests.packages.urllib3
        sys.modules['requests.packages.urllib3.contrib'] = requests.packages.urllib3.contrib
        sys.modules['requests.packages.urllib3.contrib.appengine'] = requests.packages.urllib3.contrib.appengine
        
        # Also fix the gaecontrib import issue
        try:
            from requests_toolbelt import _compat
            if not hasattr(_compat, 'gaecontrib'):
                _compat.gaecontrib = type('MockGaecontrib', (), {})()
                _compat.gaecontrib.is_appengine = lambda: False
        except ImportError:
            pass
