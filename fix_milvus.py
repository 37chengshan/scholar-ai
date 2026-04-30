import sys
content = open('apps/api/app/core/milvus_service.py').read()
content = content.replace(
    'self._connected = True',
    'self._connected = True\n            self.mode = "online"',
    1
)
content = content.replace(
    'self._connected = True',
    'self._connected = True\n                self.mode = "lite"'
)
open('apps/api/app/core/milvus_service.py', 'w').write(content)
