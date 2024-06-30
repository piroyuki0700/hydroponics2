-- MariaDB dump 10.19  Distrib 10.11.6-MariaDB, for debian-linux-gnu (aarch64)
--
-- Host: localhost    Database: hydro2024summer
-- ------------------------------------------------------
-- Server version	10.11.6-MariaDB-0+deb12u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `picture`
--

DROP TABLE IF EXISTS `picture`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `picture` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `filename` varchar(64) DEFAULT NULL,
  `taken` datetime DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pump_status`
--

DROP TABLE IF EXISTS `pump_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pump_status` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `status` varchar(16) DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pump_status`
--

LOCK TABLES `pump_status` WRITE;
/*!40000 ALTER TABLE `pump_status` DISABLE KEYS */;
INSERT INTO `pump_status` VALUES
(1,NULL,NULL);
/*!40000 ALTER TABLE `pump_status` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `refill_record`
--

DROP TABLE IF EXISTS `refill_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `refill_record` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `refilled_at` datetime DEFAULT NULL,
  `on_seconds` int(11) DEFAULT NULL,
  `trig` varchar(16) DEFAULT NULL,
  `level_before` int(11) DEFAULT NULL,
  `level_after` int(11) DEFAULT NULL,
  `upper` tinyint(1) DEFAULT NULL,
  `lower` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `report`
--

DROP TABLE IF EXISTS `report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `report` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `report_time` datetime DEFAULT NULL,
  `air_temp` float DEFAULT NULL,
  `humidity` float DEFAULT NULL,
  `water_temp` float DEFAULT NULL,
  `distance` float DEFAULT NULL,
  `water_level` float DEFAULT NULL,
  `tds_level` float DEFAULT NULL,
  `brightness` float DEFAULT NULL,
  `picture_no` int(11) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sensor_error`
--

DROP TABLE IF EXISTS `sensor_error`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sensor_error` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `water_level` int(11) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sensor_error`
--

LOCK TABLES `sensor_error` WRITE;
/*!40000 ALTER TABLE `sensor_error` DISABLE KEYS */;
INSERT INTO `sensor_error` VALUES
(1,0);
/*!40000 ALTER TABLE `sensor_error` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `setting_basic`
--

DROP TABLE IF EXISTS `setting_basic`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `setting_basic` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `myname` varchar(32) DEFAULT NULL,
  `memo` text DEFAULT NULL,
  `started` datetime DEFAULT NULL,
  `finished` datetime DEFAULT NULL,
  `uptime` datetime DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `setting_basic`
--

LOCK TABLES `setting_basic` WRITE;
/*!40000 ALTER TABLE `setting_basic` DISABLE KEYS */;
INSERT INTO `setting_basic` VALUES
(1,'水耕栽培 #1','水耕栽培テストデータ',NULL,NULL,NULL);
/*!40000 ALTER TABLE `setting_basic` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `setting_schedule`
--

DROP TABLE IF EXISTS `setting_schedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `setting_schedule` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `schedule_active` tinyint(1) DEFAULT NULL,
  `time_morning` int(11) DEFAULT NULL,
  `time_noon` int(11) DEFAULT NULL,
  `time_evening` int(11) DEFAULT NULL,
  `time_night` int(11) DEFAULT NULL,
  `morning_on` int(11) DEFAULT NULL,
  `morning_off` int(11) DEFAULT NULL,
  `noon_on` int(11) DEFAULT NULL,
  `noon_off` int(11) DEFAULT NULL,
  `evening_on` int(11) DEFAULT NULL,
  `evening_off` int(11) DEFAULT NULL,
  `nightly_active` tinyint(1) DEFAULT NULL,
  `circulator_active` tinyint(1) DEFAULT NULL,
  `time_spot1` int(11) DEFAULT NULL,
  `time_spot2` int(11) DEFAULT NULL,
  `time_spot3` int(11) DEFAULT NULL,
  `spot_on` int(11) DEFAULT NULL,
  `refill_trigger` int(11) DEFAULT NULL,
  `refill_max` int(11) DEFAULT NULL,
  `refill_days` int(11) DEFAULT NULL,
  `camera1` int(11) DEFAULT NULL,
  `camera2` int(11) DEFAULT NULL,
  `camera3` int(11) DEFAULT NULL,
  `camera4` int(11) DEFAULT NULL,
  `camera5` int(11) DEFAULT NULL,
  `notify_active` tinyint(1) DEFAULT NULL,
  `notify_time` tinyint(1) DEFAULT NULL,
  `emergency_active` int(11) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `setting_schedule`
--

LOCK TABLES `setting_schedule` WRITE;
/*!40000 ALTER TABLE `setting_schedule` DISABLE KEYS */;
INSERT INTO `setting_schedule` VALUES
(1,1,6,9,16,19,5,5,10,5,5,5,0,0,21,0,3,5,0,200,5,8,10,12,14,16,1,12,1);
/*!40000 ALTER TABLE `setting_schedule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `setting_sensor_limit`
--

DROP TABLE IF EXISTS `setting_sensor_limit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `setting_sensor_limit` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `air_temp_vlow` float DEFAULT NULL,
  `air_temp_low` float DEFAULT NULL,
  `air_temp_high` float DEFAULT NULL,
  `air_temp_vhigh` float DEFAULT NULL,
  `humidity_vlow` float DEFAULT NULL,
  `humidity_low` float DEFAULT NULL,
  `water_temp_vlow` float DEFAULT NULL,
  `water_temp_low` float DEFAULT NULL,
  `water_temp_high` float DEFAULT NULL,
  `water_temp_vhigh` float DEFAULT NULL,
  `water_level_vlow` float DEFAULT NULL,
  `water_level_low` float DEFAULT NULL,
  `tds_level_vlow` float DEFAULT NULL,
  `tds_level_low` float DEFAULT NULL,
  `tds_level_high` float DEFAULT NULL,
  `tds_level_vhigh` float DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `setting_sensor_limit`
--

LOCK TABLES `setting_sensor_limit` WRITE;
/*!40000 ALTER TABLE `setting_sensor_limit` DISABLE KEYS */;
INSERT INTO `setting_sensor_limit` VALUES
(1,1,5,35,40,10,30,1,5,25,35,10,25,0.2,0.5,3,5);
/*!40000 ALTER TABLE `setting_sensor_limit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sns_token`
--

DROP TABLE IF EXISTS `sns_token`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sns_token` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `twitter_api_key` varchar(64) DEFAULT NULL,
  `twitter_api_secret_key` varchar(64) DEFAULT NULL,
  `twitter_access_token` varchar(64) DEFAULT NULL,
  `twitter_access_token_secret` varchar(64) DEFAULT NULL,
  `line_access_token` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-05-08 22:17:28
