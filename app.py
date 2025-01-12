import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests

month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

def get_current_season():
    current_month = pd.Timestamp.now().month
    return month_to_season[current_month]

def is_temperature_normal(current_temp, data, city):
    current_season = get_current_season()

    seasonal_data = data[(data['season'] == current_season) & (data['city'] == city)]

    if not seasonal_data.empty:
        median = seasonal_data['temperature'].median()
        std_dev = seasonal_data['temperature'].std()

        lower_bound = median - 2 * std_dev
        upper_bound = median + 2 * std_dev

        if (current_temp < lower_bound) or (current_temp > upper_bound):
            return False  # Температура аномальная
        else:
            return True  # Температура нормальная
    else:
        return None

# Функция для загрузки данных из файла
def load_data(file):
    if file is not None:
        data = pd.read_csv(file)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        return data
    return None

# Функция для получения текущей погоды через API OpenWeatherMap
def get_current_weather(api_key, city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    return response.json()

# Функция для обнаружения аномалий на основе скользящего среднего и отклонения
def detect_anomalies(data, window_size=30):
    # Рассчитываем скользящее среднее и стандартное отклонение
    data['moving_avg'] = data['temperature'].rolling(window=window_size).mean()
    data['moving_std'] = data['temperature'].rolling(window=window_size).std()
    
    # Устанавливаем границы: ±2σ от скользящего среднего
    data['upper_bound'] = data['moving_avg'] + 2 * data['moving_std']
    data['lower_bound'] = data['moving_avg'] - 2 * data['moving_std']
    
    # Аномалии - точки за пределами этих границ
    data['anomaly'] = ((data['temperature'] > data['upper_bound']) | (data['temperature'] < data['lower_bound']))
    return data

# Функция для отображения статистики данных
def display_stats(data, city):
    st.write("Общий обзор данных:")
    st.write(data.describe())

    st.write("Количество аномальных точек за установленный период:")
    st.write(f"Аномалий: {data['anomaly'].sum()} из {len(data)} записей")

    st.write("Интервалы значений температуры:")
    st.write(f"Минимальная: {data['temperature'].min()}°C")
    st.write(f"Максимальная: {data['temperature'].max()}°C")
    
# Функция для построения графиков
def plot_data(data, city):
    st.subheader("График температурных данных с аномалиями")
    data = data[data['city'] == city]
    plt.figure(figsize=(12, 6))
    plt.plot(data['timestamp'], data['temperature'], label='Температура', color='blue', alpha=0.6)
    plt.plot(data['timestamp'], data['moving_avg'], label='Скользящее среднее', color='orange', linestyle='--')
    plt.fill_between(data['timestamp'], 
                     data['upper_bound'], 
                     data['lower_bound'], 
                     color='gray', 
                     alpha=0.2, label='Диапазон ±2σ')
    
    # Отметка аномалий на графике
    anomalies = data[data['anomaly']]
    plt.scatter(anomalies['timestamp'], anomalies['temperature'], color='red',
                label='Аномалии', zorder=10)

    plt.legend()
    plt.xlabel('Дата')
    plt.ylabel('Температура (°C)')
    plt.title('Температура и аномалии')
    plt.grid(True)
    st.pyplot(plt)
    
     # Сезонные профили температуры
    st.subheader("Сезонные профили температуры")
    seasonal_data = data.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    fig, ax = plt.subplots()
    sns.barplot(x='season', y='mean', data=seasonal_data, ax=ax, palette='coolwarm', errorbar='sd')
    ax.set_xlabel("Сезон")
    ax.set_ylabel("Средняя температура, °C")
    ax.set_title("Средняя температура по сезонам")
    st.pyplot(fig)

# Дополнительная визуализация 1: Анализ сезонных изменений
def seasonal_analysis(data):
    st.subheader("Средняя температура по сезонам для каждого города")
    seasonal_means = data.groupby(['city', 'season'])['temperature'].mean().unstack()
    st.dataframe(seasonal_means)

    fig, ax = plt.subplots(figsize=(10, 5))
    seasonal_means.plot(kind='bar', ax=ax)
    ax.set_ylabel("Средняя температура, °C")
    ax.set_title("Сезонные изменения температуры")
    st.pyplot(fig)

# Дополнительная визуализация 2: Тепловая карта месяца
def heatmap_month_analysis(data):
    st.subheader("Тепловая карта средней температуры по месяцам для каждого города")
    data['month'] = data['timestamp'].dt.month
    heatmap_data = data.groupby(['city', 'month'])['temperature'].mean().unstack()

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlGnBu", ax=ax)
    ax.set_xlabel("Месяц")
    ax.set_ylabel("Город")
    ax.set_title("Средняя температура по месяцам")
    st.pyplot(fig)

# Дополнительная визуализация 3: Минимальная, среднегодовая и максимальная температура
def yearly_temp_analysis(data):
    st.subheader("Минимальная, среднегодовая и максимальная температура для каждого города")
    yearly_data = data.groupby('city')['temperature'].agg(['min', 'mean', 'max'])

    st.write(yearly_data)

    fig, ax = plt.subplots(figsize=(10, 5))
    yearly_data.plot(kind='bar', ax=ax, color=['skyblue', 'green', 'orange'])
    ax.set_ylabel("Температура, °C")
    ax.set_title("Анализ температур для каждого города")
    st.pyplot(fig)


# Основной интерфейс приложения
def main():
    st.title("")
    # Загрузка файла с историческими данными
    st.sidebar.header("Загрузка данных")
    file = st.sidebar.file_uploader("Загрузите CSV-файл с данными о температуре (формат: timestamp, temp)", type=['csv'])
    api_key = st.sidebar.text_input("Введите API ключ для OpenWeatherMap", type="password")
    city = st.sidebar.text_input("Введите название города для отображения текущей температуры", value="Moscow")

    # Параметры скользящего среднего
    st.sidebar.header("Параметры анализа")
    window_size = st.sidebar.slider("Окно скользящего среднего (дни):", min_value=2, max_value=90, value=30, step=1)

    # Работа с загруженным файлом
    data = load_data(file)
    
    if data is not None:
        st.subheader("Загруженные данные")
        st.write(data.head())
        data = detect_anomalies(data, window_size=window_size)
        seasonal_analysis(data)
        yearly_temp_analysis(data)
        heatmap_month_analysis(data)
        city_list = data['city'].unique()
        city = st.sidebar.selectbox("Выберите город", city_list)
        if city:
            st.header(f"Данные для города: {city}")

            # Отображение статистики
            display_stats(data, city)

            # Построение графиков
            plot_data(data, city)
        
            # Получение текущей погоды при наличии API-ключа
            
            if api_key:
                st.subheader("Текущая температура")
                weather = get_current_weather(api_key, city)
                if weather.get("cod") == 200:
                    current_temp = weather["main"]["temp"]
                    st.write(f"Текущая температура в {city}: {current_temp} °C")

                    # Сравнение с сезонной температурой
                    if is_temperature_normal(current_temp, data, city):
                        st.write("Температура выходит за границы сезонной нормы.")
                    else:
                        st.write("Температура в пределах сезонной нормы.")
                elif weather.get("cod") == 401:
                    st.error("Ошибка: неверный API-ключ.")
                else:
                    st.error("Не удалось получить данные о погоде.")
    else:
        st.write("Пожалуйста, загрузите файл с данными, чтобы продолжить.")
if __name__ == "__main__":
    main()