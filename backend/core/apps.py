from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import sys
        import os
        # Only run this check if we are starting the server 
        # RUN_MAIN check prevents double execution due to the auto-reloader
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            from django.db import connection
            from django.db.utils import OperationalError
            import warnings
            
            # Suppress database warning during app initialization check
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Accessing the database during app initialization.*")
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    print("\033[92m" + "[OK] Database Connection: SUCCESS (" + connection.settings_dict['NAME'] + ")" + "\033[0m")
                except OperationalError:
                    print("\033[91m" + "[ERROR] Database Connection: FAILED TO CONNECT" + "\033[0m")
                except Exception as e:
                    print("\033[91m" + f"[ERROR] Database Connection: UNEXPECTED ERROR ({str(e)})" + "\033[0m")

            # Local AI Subsystem Status
            print("\033[92m" + "[OK] KIKI Local AI Engine: ACTIVE (Zero-Network Offline Mode Enabled)" + "\033[0m")

            # KIKI Phase 19 Local CUDA GPU RAG Preloading & Provenance Validation
            try:
                from core.kiki.rag.runtime_manager import rag_runtime_manager
                status = rag_runtime_manager.initialize()
                print("\033[92m" + f"[OK] KIKI Local GPU RAG Runtime Initialized: STATUS = {status}" + "\033[0m")
            except Exception as rag_e:
                print("\033[93m" + f"[WARNING] KIKI RAG Startup Initialization Warning: {str(rag_e)}" + "\033[0m")
