import pandas as pd
from datetime import datetime


class MedicalDevice:
    """Класс для медицинского оборудования"""

    # Статусы для нормализации
    STATUS_MAPPING = {
        'planned_installation': 'planned_installation',
        'планируется': 'planned_installation',
        'planned': 'planned_installation',
        'operational': 'operational',
        'op': 'operational',
        'ok': 'operational',
        'работает': 'operational',
        'maintenance_scheduled': 'maintenance_scheduled',
        'maintenance': 'maintenance_scheduled',
        'запланировано то': 'maintenance_scheduled',
        'faulty': 'faulty',
        'broken': 'faulty',
        'неисправно': 'faulty',
        'не работает': 'faulty'
    }

    def __init__(self, device_data: pd.Series):
        """Инициализация устройства на основе строки данных"""

        self.device_id = device_data.get('device_id')
        self.clinic_id = device_data.get('clinic_id')
        self.clinic_name = device_data.get('clinic_name')
        self.city = device_data.get('city')
        self.department = device_data.get('department')
        self.model = device_data.get('model')
        self.serial_number = device_data.get('serial_number')
        self.install_date = self.parse_date(device_data.get('install_date'))
        self.status = self.normalize_status(device_data.get('status'))
        self.warranty_until = self.parse_date(device_data.get('warranty_until'))
        self.last_calibration_date = self.parse_date(device_data.get('last_calibration_date'))
        self.last_service_date = self.parse_date(device_data.get('last_service_date'))
        self.issues_reported_12mo = self.parse_numeric(device_data.get('issues_reported_12mo'))
        self.failure_count_12mo = self.parse_numeric(device_data.get('failure_count_12mo'))
        self.uptime_pct = self.parse_uptime(device_data.get('uptime_pct'))
        self.issues_text = device_data.get('issues_text', '')

    def parse_date(self, date_value):
        """Парсинг даты из различных форматов"""

        if pd.isna(date_value) or date_value is None:
            return None

        try:
            if isinstance(date_value, (datetime, pd.Timestamp)):
                return pd.to_datetime(date_value)
            elif isinstance(date_value, str):

                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
                    try:
                        return pd.to_datetime(datetime.strptime(date_value, fmt))
                    except ValueError:
                        continue

            return None
        except:
            return None

    def normalize_status(self, status):
        """Нормализация статуса устройства"""

        if pd.isna(status) or status is None:
            return 'unknown'

        status_str = str(status).lower().strip()
        return self.STATUS_MAPPING.get(status_str, 'unknown')

    def parse_numeric(self, value):
        """Парсинг числовых значений"""

        try:
            if pd.isna(value):
                return 0
            return int(float(value))
        except:
            return 0

    def parse_uptime(self, value):
        """Парсинг процента времени работы"""

        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, str) and '%' in value:
                return float(value.replace('%', '').strip()) / 100
            return float(value)
        except:
            return 0.0

    def is_under_warranty(self):
        """Проверка, находится ли устройство на гарантии"""

        if self.warranty_until is None:
            return False
        return self.warranty_until > datetime.now()

    def needs_calibration(self):
        """Проверка, требуется ли калибровка (более года назад)"""

        if self.last_calibration_date is None:
            return True
        days_since_calibration = (datetime.now() - self.last_calibration_date).days
        return days_since_calibration > 365


class MedicalDeviceAnalyzer:
    """Класс для анализа медицинского оборудования"""

    def __init__(self, file_path: str):
        """Инициализация анализатора с загрузкой данных"""

        self.file_path = file_path
        self.df = pd.read_excel(file_path)
        self.devices = [MedicalDevice(row) for _, row in self.df.iterrows()]
        print(f"Загружено {len(self.devices)} устройств")

    def filter_by_warranty(self):
        """Фильтрация данных по гарантии"""

        warranty_data = []
        for device in self.devices:
            warranty_data.append({
                'device_id': device.device_id,
                'clinic_name': device.clinic_name,
                'model': device.model,
                'warranty_until': device.warranty_until,
                'under_warranty': device.is_under_warranty(),
                'status': device.status
            })

        df_result = pd.DataFrame(warranty_data)

        print(f"Устройств на гарантии: {df_result['under_warranty'].sum()}")
        print(f"Устройств с истекшей гарантией: {(~df_result['under_warranty']).sum()}")

        return df_result

    def find_clinics_with_most_problems(self, top_n=10):
        """Найти клиники с наибольшим количеством проблем"""

        clinic_problems = []

        for device in self.devices:
            problem_score = (device.issues_reported_12mo * 10 +
                             device.failure_count_12mo * 20 +
                             (50 if device.uptime_pct < 0.95 else 0) +
                             (100 if device.status == 'faulty' else 0))

            clinic_problems.append({
                'clinic_id': device.clinic_id,
                'clinic_name': device.clinic_name,
                'city': device.city,
                'problem_score': problem_score,
                'issues_count': device.issues_reported_12mo,
                'failures_count': device.failure_count_12mo,
                'devices_count': 1
            })

        df_problems = pd.DataFrame(clinic_problems)

        clinic_agg = df_problems.groupby(['clinic_id', 'clinic_name', 'city']).agg({
            'problem_score': 'sum',
            'issues_count': 'sum',
            'failures_count': 'sum',
            'devices_count': 'count'
        }).reset_index()

        clinic_agg = clinic_agg.sort_values('problem_score', ascending=False).head(top_n)

        print("Клиники с наибольшим количеством проблем")
        print(clinic_agg[['clinic_name', 'city', 'problem_score', 'issues_count', 'failures_count', 'devices_count']])

        return clinic_agg

    def build_calibration_report(self):
        """Построение отчёта по срокам калибровки"""

        calibration_data = []

        for device in self.devices:
            calibration_data.append({
                'device_id': device.device_id,
                'clinic_name': device.clinic_name,
                'model': device.model,
                'last_calibration_date': device.last_calibration_date,
                'install_date': device.install_date,
                'needs_calibration': device.needs_calibration(),
                'days_since_calibration': (
                            datetime.now() - device.last_calibration_date).days if device.last_calibration_date else None,
                'status': device.status
            })

        df_calibration = pd.DataFrame(calibration_data)

        print("Отчёт по срокам калибровки")
        print(f"Всего устройств: {len(df_calibration)}")
        print(f"Требуют калибровки: {df_calibration['needs_calibration'].sum()}")
        print(f"Нет данных: {df_calibration['last_calibration_date'].isna().sum()}")

        return df_calibration

    def create_pivot_table(self):
        """Составить сводную таблицу по клиникам и оборудованию"""

        pivot_data = []

        for device in self.devices:
            pivot_data.append({
                'clinic_name': device.clinic_name,
                'city': device.city,
                'model': device.model,
                'status': device.status,
                'under_warranty': device.is_under_warranty(),
                'needs_calibration': device.needs_calibration(),
                'issues_reported': device.issues_reported_12mo,
                'failures': device.failure_count_12mo,
                'uptime_pct': device.uptime_pct,
                'device_id': device.device_id
            })

        df_pivot = pd.DataFrame(pivot_data)

        pivot_table = pd.pivot_table(
            df_pivot,
            values=['device_id', 'issues_reported', 'failures', 'uptime_pct'],
            index=['clinic_name', 'city'],
            columns=['model'],
            aggfunc={
                'device_id': 'count',
                'issues_reported': 'sum',
                'failures': 'sum',
                'uptime_pct': 'mean'
            },
            fill_value=0
        )

        pivot_table.columns = [f'{col[1]}_{col[0]}' for col in pivot_table.columns]

        print("Сводная таблица по клиникам и оборудованию")
        print(f"Создана сводная таблица: {pivot_table.shape[0]} клиник, {pivot_table.shape[1]} показателей")

        return pivot_table

    def generate_all_reports(self, output_file='medical_devices_report.xlsx'):
        """Генерация всех отчётов и сохранение в Excel"""

        print("Анализ мед. оборудования")

        warranty_df = self.filter_by_warranty()
        problems_df = self.find_clinics_with_most_problems()
        calibration_df = self.build_calibration_report()
        pivot_df = self.create_pivot_table()

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            warranty_df.to_excel(writer, sheet_name='Гарантия', index=False)
            problems_df.to_excel(writer, sheet_name='Проблемные_клиники', index=False)
            calibration_df.to_excel(writer, sheet_name='Калибровка', index=False)
            pivot_df.to_excel(writer, sheet_name='Сводная_таблица')

        print(f"\nОтчёты сохранены в файл: {output_file}")


def main():
    """Основная функция для выполнения задания"""

    file_path = 'medical_diagnostic_devices_10000.xlsx'  # Путь к файлу с данными

    try:
        analyzer = MedicalDeviceAnalyzer(file_path)
        analyzer.generate_all_reports()

        print("Задание выполнено")

    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
    except Exception as e:
        print(f"Ошибка при выполнении: {e}")


if __name__ == "__main__":
    main()