import traceback
from PySide6.QtCore import QObject, Signal, Slot, QThread
import time

import os
import shutil
from logger import AppLogger
from quick_start import merge_blacklist, merge_settings
from _data import BACKUP_SETTINGS_FILE_PATH, DIRECTORY, DEBUG, GOODBYE_DPI_PATH, LOG_LEVEL, SETTINGS_FILE_PATH, VERSION, settings

logger = AppLogger(VERSION, 'after_update', LOG_LEVEL)

class AfterUpdateHelper(QObject):
    progressIndeterminateVisibleChanged = Signal(bool)
    progressVisibleChanged = Signal(bool)
    progressValueChanged = Signal(int)
    remainingTimeChanged = Signal('QVariantList')
    updateMovingSettingsCompleted = Signal()
    updateCleanupStarted = Signal()
    updateCleanupCompleted = Signal()
    updateComponentsStarted = Signal()
    updateComponentsCompleted = Signal()
    
    def __init__(self):
        super().__init__()
        self.worker_thread = None

    @Slot()
    def startUpdateProcess(self):
        self.startMovingSettings()

    def startMovingSettings(self):
        self.worker_thread = QThread()
        self.worker = MovingSettingsWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker.progressVisibleChanged.connect(self.progressVisibleChanged)
        self.worker.progressValueChanged.connect(self.progressValueChanged)
        self.worker.finished.connect(self.movingSettingsFinished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    @Slot()
    def movingSettingsFinished(self):
        self.updateMovingSettingsCompleted.emit()
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.startCleanup()

    def startCleanup(self):
        self.progressIndeterminateVisibleChanged.emit(True)
        self.updateCleanupStarted.emit()
        self.worker_thread = QThread()
        self.worker = CleanupWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker.progressVisibleChanged.connect(self.progressVisibleChanged)
        self.worker.progressValueChanged.connect(self.progressValueChanged)
        self.worker.remainingTimeChanged.connect(self.remainingTimeChanged)
        self.worker.finished.connect(self.cleanupFinished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    @Slot()
    def cleanupFinished(self):
        self.progressIndeterminateVisibleChanged.emit(False)
        self.updateCleanupCompleted.emit()
        self.worker_thread.quit()
        self.worker_thread.wait()
        
        self.startUpdatingComponents()

    def startUpdatingComponents(self):
        self.updateComponentsStarted.emit()

        self.worker_thread = QThread()
        self.worker = UpdateComponentsWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker.progressVisibleChanged.connect(self.progressVisibleChanged)
        self.worker.progressValueChanged.connect(self.progressValueChanged)
        self.worker.finished.connect(self.updateComponentsFinished)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    @Slot()
    def updateComponentsFinished(self):
        self.updateComponentsCompleted.emit()
        self.worker_thread.quit()
        self.worker_thread.wait()

class MovingSettingsWorker(QObject):
    progressVisibleChanged = Signal(bool)
    progressValueChanged = Signal(int)
    finished = Signal()

    def run(self):
        source_dir = DIRECTORY + '_internal/data' if not DEBUG else "E:/_component/data1"
        dest_dir = DIRECTORY + 'data' if not DEBUG else "E:/_component/data"
        if os.path.exists(source_dir):
            try:
                files_to_move = []
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        if file.endswith('.txt'):
                            source_file = os.path.join(root, file)
                            relative_path = os.path.relpath(source_file, source_dir)
                            dest_file = os.path.join(dest_dir, relative_path)
                            files_to_move.append((source_file, dest_file))

                total_files = len(files_to_move)
                
                if not merge_settings(source_dir+"/settings/_settings.ini", dest_dir+"/settings/settings.ini"):
                    logger.raise_warning("The update could not be completed correctly. Your data may be lost.\n\n" +\
                                        f"Backup settings file {source_dir+'/settings/_settings.ini'} does not exist.")
                settings.reload_settings()
                
                if total_files == 0:
                    self.finished.emit()
                    return
                
                time.sleep(5)
                self.progressVisibleChanged.emit(True)
                for index, (source_file, dest_file) in enumerate(files_to_move):
                    try:
                        dest_file_dir = os.path.dirname(dest_file)
                        if not os.path.exists(dest_file_dir):
                            os.makedirs(dest_file_dir)

                        shutil.copyfile(source_file, dest_file)

                        progress = int((index + 1) / total_files * 100)
                        self.progressValueChanged.emit(progress)
                    except Exception as e:
                        logger.create_error_log(f"Error moving file {source_file} to {dest_file}: {e}")

                self.progressVisibleChanged.emit(False)
            except:
                logger.raise_warning("The update could not be completed. Your data may be lost.\n\n"+traceback.format_exc())        
        else:
            try:
                merge_settings(BACKUP_SETTINGS_FILE_PATH, SETTINGS_FILE_PATH)
                merge_blacklist(GOODBYE_DPI_PATH)
                settings.reload_settings()
                time.sleep(5)

                settings.change_setting('GLOBAL', 'after_update', 'False')
            except:
                logger.raise_warning("The update could not be completed. Your data may be lost.\n\n"+traceback.format_exc())
        
        self.finished.emit()

class CleanupWorker(QObject):
    progressVisibleChanged = Signal(bool)
    progressValueChanged = Signal(int)
    remainingTimeChanged = Signal(list)
    finished = Signal()

    def run(self):
        items_to_delete = []
        
        inte_dir = DIRECTORY + '_internal' if not DEBUG else "E:/_component/_internal"
        port_dir = DIRECTORY + '_portable.zip' if not DEBUG else "E:/_component/_portable.zip"

        if os.path.exists(inte_dir):
            items_to_delete.append(inte_dir)
        if os.path.exists(port_dir):
            items_to_delete.append(port_dir)

        total_items = 0
        time_per_item = 0.01 
        items_file_counts = {}

        for item in items_to_delete:
            if os.path.isdir(item):
                total_files = self.count_files_in_directory(item)
                items_file_counts[item] = total_files
                total_items += total_files
            elif os.path.isfile(item):
                items_file_counts[item] = 1
                total_items += 1

        if total_items == 0:
            self.finished.emit()
            return

        total_estimated_time = total_items * time_per_item

        self.progressVisibleChanged.emit(True)
        files_deleted = 0

        for item in items_to_delete:
            try:
                if os.path.isdir(item):
                    for root, dirs, files in os.walk(item, topdown=False):
                        for name in files:
                            file_path = os.path.join(root, name)
                            try:
                                os.remove(file_path)
                                files_deleted += 1
                                self.update_progress(files_deleted, total_items, total_estimated_time)
                            except Exception as e:
                                logger.create_error_log(f"Error deleting file {file_path}: {e}")
                        for name in dirs:
                            dir_path = os.path.join(root, name)
                            try:
                                os.rmdir(dir_path)
                                files_deleted += 1
                                self.update_progress(files_deleted, total_items, total_estimated_time)
                            except Exception as e:
                                logger.create_error_log(f"Error deleting directory {dir_path}: {e}")
                    try:
                        os.rmdir(item)
                        files_deleted += 1
                        self.update_progress(files_deleted, total_items, total_estimated_time)
                    except Exception as e:
                        logger.create_error_log(f"Error deleting directory {item}: {e}")
                elif os.path.isfile(item):
                    os.remove(item)
                    files_deleted += 1
                    self.update_progress(files_deleted, total_items, total_estimated_time)
            except Exception as e:
                logger.create_error_log(f"Error deleting {item}: {e}")

        self.progressVisibleChanged.emit(False)
        self.remainingTimeChanged.emit(['', 0]) 
        self.finished.emit()

    def update_progress(self, files_deleted, total_files, total_estimated_time):
        progress = int((files_deleted / total_files) * 100)
        self.progressValueChanged.emit(progress)
        elapsed_time = files_deleted * 0.01 
        remaining_time = total_estimated_time - elapsed_time
        self.emitRemainingTime(remaining_time)
        time.sleep(0.01)

    def emitRemainingTime(self, remaining_time):
        if remaining_time > 60:
            minutes_left = int(remaining_time / 60)
            remaining_time_str = [f"cleanup_c", minutes_left]
        elif remaining_time > 0:
            remaining_time_str = ["cleanup_m", 0]
        else:
            remaining_time_str = ["cleanup_e", 0]
        self.remainingTimeChanged.emit(remaining_time_str)

    def count_files_in_directory(self, directory):
        total_files = 0
        for root, dirs, files in os.walk(directory):
            total_files += len(files) + len(dirs)

        total_files += 1
        return total_files

class UpdateComponentsWorker(QObject):
    progressVisibleChanged = Signal(bool)
    progressValueChanged = Signal(int)
    finished = Signal()

    def run(self):

        import time
        self.progressVisibleChanged.emit(True)
        for i in range(101):
            time.sleep(0.03) 
            self.progressValueChanged.emit(i)
        self.progressVisibleChanged.emit(False)
        self.finished.emit()
