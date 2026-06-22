# Cuida APP 🩺

> Plataforma de salud híbrida diseñada para optimizar la supervisión remota y la gestión del cuidado de personas que requieren asistencia.

El objetivo principal de **Cuida APP** es reducir la brecha tecnológica, facilitando el seguimiento de medicaciones, eventos médicos y constantes de salud a través de una interfaz intuitiva, limpia y accesible para todo tipo de usuarios.

---

## 👥 Vinculación de Roles

El sistema opera bajo un ecosistema integral que conecta al cuidador tanto en la web como en el entorno móvil con el adulto mayor:

*   **Cuidador (Perfil de Monitoreo y Gestión - Entorno Web / Móvil):** Responsable de la supervisión a través de un tablero web centralizado y una vista adaptada en la app móvil. Desde allí administra datos, programa medicamentos, gestiona turnos médicos y monitorea la telemetría del dispositivo de los adultos mayores a su cargo.
*   **Abuelo (Perfil Asistido / Entorno Móvil):** Receptor del cuidado,  puede estar vinculado a varios cuidadores. Cuenta con una interfaz móvil sumamente simplificada que le permite registrar sus tomas diarias, visualizar recordatorios visuales estáticos y emitir alertas inmediatas ante emergencias.

---

## 🎨 Diseño y Accesibilidad

*   **👁️ Identificación Visual:** Sistema de iconografía unificado para diferenciar las secciones y reconocer las funciones principales de forma instintiva.
*   **💻 Optimización Web (Panel del Cuidador):** Menú de acceso rápido que centraliza la gestión en un solo espacio. Permite visualizar de manera inmediata el stock de medicamentos disponibles y los eventos más próximos. Además, incorpora un panel de notificaciones en tiempo real.
*   **📱 Accesibilidad Móvil: App del Abuelo** Interfaz adaptada con densidad de botones reducida, tipografías escaladas e iconografía de gran tamaño para evitar errores involuntarios de pulsación. **App del cuidador** Permite comunicarse con sus abuelos a cargo y poder monitorear los datos cargados en el perfil.

---

## 📦 Módulos y Funcionalidades

### 👤 Gestión de Perfiles
*   **Tutor:** Visualización de datos básicos y administración completa de los perfiles asignados.
*   **Paciente:** Acceso exclusivo de **solo lectura** a su información principal, resguardando la integridad de los datos clínicos.

### 🔋 Monitoreo del Dispositivo
*   Supervisión en tiempo real por parte del tutor de la **ubicación geográfica** y el **porcentaje de batería** del dispositivo del paciente.

### 📅 Calendario Inteligente
*   Programación de turnos médicos, recordatorios y eventos sociales por parte del tutor. Las alertas se sincronizan automáticamente en el dispositivo móvil del paciente de forma simplificada.

### 💊 Control de Medicamentos
*   **Tutor:** Administra el ABM (Alta, Baja y Modificación) de los remedios, que se adapta a diferentes presentaciones y frecuencias horarias que puede llegar a tener. Incluye el control de stock para gestionar reposiciones y un registro para ver el historial de tomas de los remedios. 
*   **Paciente:** Registro de la toma efectiva del fármaco y visualización de un resumen digital de su tratamiento para consultas médicas.

### 📸 Gestión de Archivos (Fotos)
Centraliza las imágenes capturadas por el paciente para que el tutor las procese y digitalice:
*   **Turnos o invitaciones** ➡️ Se desglosan en el *Calendario*.
*   **Recetas e indicaciones** ➡️ Se vinculan al módulo de *Medicamentos*.
*   **Capturas de pantallas de dispositivos clínicos** (tensiómetros, balanzas) ➡️ Se derivan a *Mediciones*.

### 📊 Mediciones Clínicas
*   Panel donde el tutor visualiza la **evolución gráfica** de las variables de salud registradas por el paciente. El sistema está parametrizado para el control de glucosa, presión arterial y peso corporal.

### 💊 Control de Medicamentos y Alarmas
* Visualización de la pauta de tratamiento activa, indicando con claridad la hora de la siguiente toma del abuelo. 
* **Cuidador:** Carga y control del stock y cantidades para la organización centralizada de las alarmas.
* **Abuelo:** Interfaz adaptada con alertas visuales aumentadas que confirman el registro de la toma efectiva del fármaco.

### 📸 Gestión de Archivos y Almacenamiento en la Nube
* Módulo de captura y carga multimedia que permite al abuelo fotografiar recetas, indicaciones o pantallas de dispositivos clínicos (tensiómetros/balanzas). La app envía los archivos de forma optimizada hacia el servidor para su persistencia en la nube y posterior procesamiento gráfico.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Backend / API Server** | Python 3.x & Django 5.x | Arquitectura dual: MVT para la web y Django REST Framework (DRF) para la app móvil. |
| **App Móvil (Abuelo / Cuidador)** | Flutter & Dart | Interfaz nativa cross-platform de alta accesibilidad y alto rendimiento. |
| **Panel Web (Tutor)** | HTML5, CSS3 & JavaScript | Frontend modular con manipulación dinámica del DOM (Vanilla JS). |
| **Base de Datos** | SQLite | Diseño relacional estructurado para la persistencia de usuarios y métricas. |
| **Integraciones** | FullCalendar API | Renderizado dinámico e interactivo de la agenda médica en la web. |
| **Infraestructura Cloud** | Render, Neon (PostgreSQL) & Cloudinary |

---

## 🔄 Flujo de Comunicación (Django ⇄ Flutter)

*   **Consumo de APIs Asincrónicas:** La aplicación en Flutter se conecta de forma segura a la URL de producción alojada en Render. Al registrar una acción (como la telemetría automática del teléfono, la subida de un documento multimedia o el registro de la toma de un medicamento), se despacha un JSON que impacta en la base de datos PostgreSQL de Neon para actualizar instantáneamente las pantallas de monitoreo.
* *   **Sincronización de Agenda:** Los eventos programados por el tutor en el calendario web se serializan en formato JSON, permitiendo que la app del paciente los reciba y los parsee localmente para configurar los recordatorios en el teléfono. Para evitar descalces horarios, los datos se procesan bajo un esquema **Timezone Aware (Huso Horario Local)**.

