import os
from supabase import create_client, Client

_url: str = os.environ["SUPABASE_URL"]
_anon_key: str = os.environ["SUPABASE_ANON_KEY"]
_service_role_key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# 一般驗證用（anon key）
supabase: Client = create_client(_url, _anon_key)

# 後端管理用（service_role key）— 絕不回傳給前端
supabase_admin: Client = create_client(_url, _service_role_key)
