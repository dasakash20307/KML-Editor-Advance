import datetime
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMessageBox

class LockHandler(QObject):
    def __init__(self, main_window_ref, db_lock_manager, kml_file_lock_manager, credential_manager,
                 log_message_callback, update_status_bar_callback,
                 max_lock_retries, lock_retry_timeout_ms, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref 
        self.db_lock_manager = db_lock_manager
        self.kml_file_lock_manager = kml_file_lock_manager
        self.credential_manager = credential_manager
        self.log_message_callback = log_message_callback
        self.update_status_bar_callback = update_status_bar_callback
        
        self.max_db_lock_retries = max_lock_retries
        self.db_lock_retry_timeout_ms = lock_retry_timeout_ms
        self.max_kml_lock_retries = max_lock_retries 
        self.kml_lock_retry_timeout_ms = lock_retry_timeout_ms 

        self.db_lock_retry_timer = QTimer(self)
        self.db_lock_retry_timer.setSingleShot(True)
        self.db_lock_retry_timer.timeout.connect(self._handle_db_lock_retry_timeout)
        self.db_lock_retry_attempts = 0
        self.current_db_retry_operation = None
        self.current_db_retry_args = None
        self.current_db_retry_kwargs = None

        self.kml_lock_retry_timer = QTimer(self)
        self.kml_lock_retry_timer.setSingleShot(True)
        self.kml_lock_retry_timer.timeout.connect(self._handle_kml_lock_retry_timeout)
        self.kml_lock_retry_attempts = 0
        self.current_kml_retry_operation = None
        self.current_kml_retry_args = None
        self.current_kml_retry_kwargs = None

    def _reset_db_retry_state(self): 
        self.db_lock_retry_attempts = 0
        self.current_db_retry_operation = None
        self.current_db_retry_args = None
        self.current_db_retry_kwargs = None
        if self.db_lock_retry_timer.isActive():
            self.db_lock_retry_timer.stop()

    def _handle_db_lock_retry_timeout(self):
        if self.current_db_retry_operation:
            operation_name = self.current_db_retry_operation.__name__ if hasattr(self.current_db_retry_operation, '__name__') else str(self.current_db_retry_operation)
            self.log_message_callback(f"DB Lock retry timer timeout. Re-attempting original operation: {operation_name}", "info")

            operation_to_call = self.current_db_retry_operation
            args = self.current_db_retry_args if self.current_db_retry_args is not None else []
            kwargs = self.current_db_retry_kwargs if self.current_db_retry_kwargs is not None else {}

            if callable(operation_to_call):
                operation_to_call(*args, **kwargs) 
            else:
                self.log_message_callback(f"Error: Stored DB retry operation {operation_name} is not callable.", "error")
                self._reset_db_retry_state()
        else:
            self.log_message_callback("LockHandler WARN: _handle_db_lock_retry_timeout called with no current_db_retry_operation.", "warning")
            self._reset_db_retry_state()

    def _reset_kml_retry_state(self):
        self.kml_lock_retry_attempts = 0
        self.current_kml_retry_operation = None
        self.current_kml_retry_args = None
        self.current_kml_retry_kwargs = None
        if self.kml_lock_retry_timer.isActive():
            self.kml_lock_retry_timer.stop()

    def _handle_kml_lock_retry_timeout(self):
        if not self.current_kml_retry_operation:
            self.log_message_callback("KML Lock retry timeout with no operation stored. Resetting.", "warning")
            self._reset_kml_retry_state()
            return

        operation_name = getattr(self.current_kml_retry_operation, '__name__', 'Unnamed KML operation')

        if self.kml_lock_retry_attempts > 0: 
            self.log_message_callback(f"KML Lock retry timer timeout for {operation_name}. Attempts remaining: {self.kml_lock_retry_attempts}", "info")
            operation_to_call = self.current_kml_retry_operation
            args = self.current_kml_retry_args if self.current_kml_retry_args is not None else []
            kwargs = self.current_kml_retry_kwargs if self.current_kml_retry_kwargs is not None else {}
            
            self.log_message_callback(f"Retrying {operation_name}. Attempts left: {self.kml_lock_retry_attempts}", "debug")

            if callable(operation_to_call):
                operation_to_call(*args, **kwargs)
            else:
                self.log_message_callback(f"Error: Stored KML retry operation {operation_name} is not callable.", "error")
                self._reset_kml_retry_state()
        else: 
            self.log_message_callback(f"Max KML lock retries reached for {operation_name}. Operation aborted.", "error")
            QMessageBox.warning(self.main_window_ref, "KML Lock Busy",
                                f"Could not acquire lock for KML operation '{operation_name}' after multiple retries. Please try again later.")
            self._reset_kml_retry_state()


    def _execute_kml_operation_with_lock(self, kml_filename: str, operation_callable: callable,
                                         operation_type_for_retry: str, 
                                         original_public_method_ref: callable,
                                         original_public_method_args: tuple,
                                         original_public_method_kwargs: dict,
                                         *args_for_op_callable, **kwargs_for_op_callable):
        if not self.kml_file_lock_manager:
            self.log_message_callback(f"Cannot perform '{operation_type_for_retry}' on '{kml_filename}': KMLFileLockManager not initialized.", "critical")
            QMessageBox.critical(self.main_window_ref, "Critical Error", "KML File Lock Manager not available. Please restart.")
            return None

        is_new_retry_series = not (self.current_kml_retry_operation == original_public_method_ref and
                                   self.current_kml_retry_args == original_public_method_args and
                                   self.current_kml_retry_kwargs == original_public_method_kwargs)

        if is_new_retry_series:
            self._reset_kml_retry_state()
            self.kml_lock_retry_attempts = self.max_kml_lock_retries 

        lock_status = self.kml_file_lock_manager.acquire_kml_lock(kml_filename, operation_description=operation_type_for_retry)
        result = None

        if lock_status is True:
            self.log_message_callback(f"KML lock acquired for '{kml_filename}' ({operation_type_for_retry}). Executing.", "info")
            self._reset_kml_retry_state() 
            try:
                result = operation_callable(*args_for_op_callable, **kwargs_for_op_callable)
            except Exception as e:
                self.log_message_callback(f"Exception during KML locked operation '{operation_type_for_retry}' on '{kml_filename}': {e}", "error")
                QMessageBox.critical(self.main_window_ref, "Operation Error", f"An error occurred during '{operation_type_for_retry}' on '{kml_filename}':\n{e}")
                result = None 
            finally:
                self.kml_file_lock_manager.release_kml_lock(kml_filename)
            return result

        elif lock_status == "STALE_LOCK_DETECTED":
            self._reset_kml_retry_state() 
            lock_info = self.kml_file_lock_manager.get_kml_lock_info(kml_filename)
            holder_nickname = lock_info.get('holder_nickname', 'Unknown') if lock_info else 'Unknown'

            reply = QMessageBox.question(self.main_window_ref, "Stale KML Lock",
                                         f"KML file '{kml_filename}' is locked by '{holder_nickname}', but the lock appears stale.\nDo you want to override it?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.kml_file_lock_manager.force_acquire_kml_lock(kml_filename, operation_description=f"Forced {operation_type_for_retry}"):
                    self.log_message_callback(f"KML lock forcibly acquired for '{kml_filename}'. Executing '{operation_type_for_retry}'.", "info")
                    try:
                        result = operation_callable(*args_for_op_callable, **kwargs_for_op_callable)
                    except Exception as e_force:
                        self.log_message_callback(f"Exception during KML locked op (force acquire) '{operation_type_for_retry}' on '{kml_filename}': {e_force}", "error")
                        result = None
                    finally:
                        self.kml_file_lock_manager.release_kml_lock(kml_filename)
                    return result
                else:
                    QMessageBox.critical(self.main_window_ref, "Lock Override Failed", f"Failed to override the stale KML lock for '{kml_filename}'.")
                    return None
            else:
                self.log_message_callback(f"User chose not to override stale KML lock for '{kml_filename}'. Operation '{operation_type_for_retry}' aborted.", "info")
                return None

        elif lock_status is False: 
            if self.kml_lock_retry_attempts > 0:
                self.current_kml_retry_operation = original_public_method_ref
                self.current_kml_retry_args = original_public_method_args
                self.current_kml_retry_kwargs = original_public_method_kwargs
                
                self.kml_lock_retry_attempts -= 1 
                self.log_message_callback(f"KML file '{kml_filename}' is locked. Will retry '{operation_type_for_retry}'. Attempts left: {self.kml_lock_retry_attempts}", "warning")
                if self.update_status_bar_callback: 
                    self.update_status_bar_callback(f"KML file '{kml_filename}' is locked. Retrying {self.kml_lock_retry_attempts} more times...")
                self.kml_lock_retry_timer.start(self.kml_lock_retry_timeout_ms)
                return "RETRYING" 
            else: 
                self.log_message_callback(f"Max KML lock retries reached for '{kml_filename}' ({operation_type_for_retry}). Operation aborted.", "error")
                QMessageBox.warning(self.main_window_ref, "KML File Busy", f"KML file '{kml_filename}' is locked by another process. Please try again later.")
                self._reset_kml_retry_state()
                return None

        elif lock_status == "ERROR":
            self.log_message_callback(f"Error acquiring KML lock for '{kml_filename}' ({operation_type_for_retry}).", "error")
            QMessageBox.critical(self.main_window_ref, "KML Lock Error", f"An error occurred while trying to lock KML file '{kml_filename}'. Check logs.")
            self._reset_kml_retry_state()
            return None
        
        self.log_message_callback(f"Unhandled KML lock status '{lock_status}' for '{kml_filename}'. Operation aborted.", "error")
        self._reset_kml_retry_state()
        return None

    def _execute_db_operation_with_lock(self, operation_callable, operation_desc, lock_duration=60,
                                        retry_callable_for_timer=None, 
                                        args_for_retry_callable=None,
                                        kwargs_for_retry_callable=None):
        result_from_callable = None
        if not self.db_lock_manager:
            self.log_message_callback(f"Cannot perform '{operation_desc}': DatabaseLockManager not initialized.", "critical")
            QMessageBox.critical(self.main_window_ref, "Critical Error", "Database Lock Manager not available. Please restart.")
            return False, None

        if self.current_db_retry_operation != retry_callable_for_timer: 
            self.db_lock_retry_attempts = 0 

        lock_status = self.db_lock_manager.acquire_lock(lock_duration, operation_desc)
        callable_execution_succeeded = False # Default to False, will be updated by op_callable result or error

        if lock_status is True:
            self.log_message_callback(f"Lock acquired for '{operation_desc}'. Executing operation.", "info")
            self._reset_db_retry_state() 
            try:
                if callable(operation_callable):
                    result_from_callable = operation_callable()
                    callable_execution_succeeded = result_from_callable # Assuming direct result indicates success
                else:
                    self.log_message_callback(f"Error: operation_callable for '{operation_desc}' is not callable.", "error")
                    callable_execution_succeeded = False # Or None, as per new logic for non-execution
                    result_from_callable = None # Explicitly set to None as callable was not valid
            except Exception as e:
                self.log_message_callback(f"Exception during locked operation '{operation_desc}': {e}", "error")
                QMessageBox.critical(self.main_window_ref, "Operation Error", f"An error occurred during '{operation_desc}':\n{e}")
                callable_execution_succeeded = False
                result_from_callable = False # As per "If an exception occurs... return True, False"
            finally:
                self.db_lock_manager.release_lock()
            # If callable was not callable, result_from_callable is None.
            # If callable raised exception, result_from_callable is False.
            # Otherwise, result_from_callable holds the actual return value.
            # The first element of the tuple is True because lock was acquired and attempt was made.
            if not callable(operation_callable):
                 return True, None # Attempted, but callable was invalid.
            return True, result_from_callable

        elif lock_status == "STALE_LOCK_DETECTED":
            self._reset_db_retry_state() 
            lock_info = self.db_lock_manager.get_current_lock_info()
            holder_nickname = lock_info.get('holder_nickname', 'Unknown') if lock_info else 'Unknown'
            stale_op_desc = lock_info.get('operation_description', 'unknown operation') if lock_info else 'unknown'

            reply = QMessageBox.question(self.main_window_ref, "Stale Database Lock",
                                         f"The database lock held by '{holder_nickname}' for operation '{stale_op_desc}' appears to be stale.\n\nDo you want to override this lock?\n\nOverriding might be risky if the other process is still active but unresponsive.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message_callback(f"User chose to override stale lock for '{operation_desc}'.", "info")
                if self.db_lock_manager.force_acquire_lock(lock_duration, operation_desc):
                    self.log_message_callback(f"Lock forcibly acquired for '{operation_desc}'. Executing operation.", "info")
                    try:
                        if callable(operation_callable):
                            result_from_callable = operation_callable()
                            # callable_execution_succeeded = result_from_callable # Not needed, directly use result_from_callable
                        else:
                             result_from_callable = None # Invalid callable
                    except Exception as e:
                        self.log_message_callback(f"Exception during locked operation (after force acquire) '{operation_desc}': {e}", "error")
                        QMessageBox.critical(self.main_window_ref, "Operation Error", f"An error occurred during '{operation_desc}' after overriding lock:\n{e}")
                        result_from_callable = False # Exception means operation failed
                    finally:
                        self.db_lock_manager.release_lock()
                    if not callable(operation_callable):
                        return True, None # Attempted, but callable was invalid.
                    return True, result_from_callable
                else:
                    self.log_message_callback(f"Failed to force acquire lock for '{operation_desc}'.", "error")
                    QMessageBox.critical(self.main_window_ref, "Lock Override Failed", "Could not override the stale lock. The original lock might still be active or there was a file system error.")
                    return False, None
            else:
                self.log_message_callback(f"User chose not to override stale lock for '{operation_desc}'. Operation aborted.", "info")
                return False, None

        elif lock_status is False: 
            if self.db_lock_retry_attempts < self.max_db_lock_retries:
                self.db_lock_retry_attempts += 1
                self.current_db_retry_operation = retry_callable_for_timer 
                self.current_db_retry_args = args_for_retry_callable if args_for_retry_callable is not None else []
                self.current_db_retry_kwargs = kwargs_for_retry_callable if kwargs_for_retry_callable is not None else {}

                lock_info = self.db_lock_manager.get_current_lock_info()
                holder_nickname = lock_info.get('holder_nickname', 'Unknown') if lock_info else 'Unknown'
                locked_op_desc = lock_info.get('operation_description', 'unknown operation') if lock_info else 'unknown'

                self.log_message_callback(f"Database locked by {holder_nickname} (for '{locked_op_desc}'). Will retry '{operation_desc}' in {self.db_lock_retry_timeout_ms / 1000}s (Attempt {self.db_lock_retry_attempts}/{self.max_db_lock_retries}).", "warning")
                self.db_lock_retry_timer.start(self.db_lock_retry_timeout_ms)
            else:
                self.log_message_callback(f"Max lock retry attempts ({self.max_db_lock_retries}) reached for '{operation_desc}'. Operation aborted.", "error")
                QMessageBox.warning(self.main_window_ref, "Database Busy", f"The database is still locked by another process after {self.max_db_lock_retries} retries. Please try '{operation_desc}' again later.")
                self._reset_db_retry_state()
            return False, None

        elif lock_status == "ERROR":
            self._reset_db_retry_state()
            self.log_message_callback(f"Failed to acquire lock for '{operation_desc}' due to an internal error in DatabaseLockManager.", "critical")
            QMessageBox.critical(self.main_window_ref, "Lock Acquisition Error", "Could not acquire database lock due to an internal error. Please check the logs.")
            return False, None

        self.log_message_callback(f"Unhandled lock status '{lock_status}' for '{operation_desc}'. Operation aborted.", "error")
        self._reset_db_retry_state()
        return False, None
