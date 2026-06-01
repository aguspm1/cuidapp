# Cuida APP 🩺

> Plataforma de salud híbrida diseñada para optimizar la supervisión remota y la gestión del cuidado de personas que requieren asistencia.

El objetivo principal de **Cuida APP** es reducir la brecha tecnológica, facilitando el seguimiento de medicaciones, eventos médicos y constantes de salud a través de una interfaz intuitiva, limpia y accesible para todo tipo de usuarios.

---

## 👥 Vinculación de Roles

El sistema opera bajo un ecosistema dual que conecta al cuidador con el entorno del paciente:

*   **Tutor (Perfil Administrativo / Entorno Web):** Responsable de la gestión integral a través de un tablero de control centralizado. Desde aquí administra datos del paciente, programa medicaciones, gestiona la agenda de eventos y monitorea el estado del dispositivo de las personas a su cargo.
*   **Paciente (Perfil Asistido / Entorno Móvil):** Receptor del cuidado. Cuenta con una aplicación móvil de diseño simplificado que le permite visualizar sus pautas diarias y emitir alertas inmediatas ante situaciones de emergencia.

---

## 🎨 Diseño y Accesibilidad

*   **👁️ Identificación Visual:** Sistema de iconografía unificado para diferenciar las secciones y reconocer las funciones principales de forma instintiva.
*   **💻 Optimización Web (Panel del Tutor):** Menú de acceso rápido que centraliza la gestión en un solo espacio. Permite visualizar de manera inmediata el stock de medicamentos disponibles y los eventos más próximos.
*   **📱 Accesibilidad Móvil (App del Paciente):** Interfaz móvil adaptada con densidad de botones reducida, tipografías escaladas e iconografía de gran tamaño para evitar errores involuntarios de pulsación.

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
*   **Tutor:** Gestión ABM (Alta, Baja y Modificación) de remedios. Al ingresar el contenido de las cajas y la frecuencia de las dosis, el sistema genera alertas de consumo y notificaciones automáticas de reposición de stock.
*   **Paciente:** Registro de la toma efectiva del fármaco y visualización de un resumen digital de su tratamiento para consultas médicas.

### 📸 Gestión de Archivos (Fotos)
Centraliza las imágenes capturadas por el paciente para que el tutor las procese y digitalice:
*   **Turnos o invitaciones** ➡️ Se desglosan en el *Calendario*.
*   **Recetas e indicaciones** ➡️ Se vinculan al módulo de *Medicamentos*.
*   **Capturas de pantallas de dispositivos clínicos** (tensiómetros, balanzas) ➡️ Se derivan a *Mediciones*.

### 📊 Mediciones Clínicas
*   Panel donde el tutor visualiza la **evolución gráfica** de las variables de salud registradas por el paciente. El sistema está parametrizado para el control de glucosa, presión arterial y peso corporal.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Backend / API Server** | Python 3.x & Django 5.x | Arquitectura dual: MVT para la web y API REST (`JsonResponse`) para la app móvil. |
| **App Móvil (Paciente)** | Flutter & Dart | Interfaz nativa cross-platform de alta accesibilidad y alto rendimiento. |
| **Panel Web (Tutor)** | HTML5, CSS3 & JavaScript | Frontend modular con manipulación dinámica del DOM (Vanilla JS). |
| **Base de Datos** | SQLite | Diseño relacional estructurado para la persistencia de usuarios y métricas. |
| **Integraciones** | FullCalendar API | Renderizado dinámico e interactivo de la agenda médica en la web. |

---

## 🔄 Flujo de Comunicación (Django ⇄ Flutter)

*   **Consumo de APIs Asincrónicas:** La aplicación en Flutter se conecta mediante peticiones HTTP a los endpoints de Django. Al registrar una acción (como la toma de un medicamento o un botón de alerta), se envía un paquete JSON que el backend procesa para notificar al instante en el panel del tutor.
*   **Sincronización y Serialización:** Los eventos del calendario web se **serializan** en formato JSON en el servidor. La app móvil los recibe, los **parsea** localmente y configura los recordatorios nativos en el teléfono del paciente.

