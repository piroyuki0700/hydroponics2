-- MySQL dump 10.15  Distrib 10.0.28-MariaDB, for debian-linux-gnueabihf (armv7l)
--
-- Host: hydro2022summer    Database: hydro2022summer
-- ------------------------------------------------------
-- Server version	10.0.28-MariaDB-2+b1

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
) ENGINE=InnoDB AUTO_INCREMENT=257 DEFAULT CHARSET=utf8mb4;
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `refill_record`
--

DROP TABLE IF EXISTS `refill_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `refill_record` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `on_seconds` int(11) DEFAULT NULL,
  `level_before` int(11) DEFAULT NULL,
  `level_after` int(11) DEFAULT NULL,
  `refilled_at` datetime DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
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
) ENGINE=InnoDB AUTO_INCREMENT=666 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `setting_basic`
--

DROP TABLE IF EXISTS `setting_basic`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `setting_basic` (
  `no` int(11) NOT NULL AUTO_INCREMENT,
  `myname` varchar(32) DEFAULT NULL,
  `memo` text,
  `started` datetime DEFAULT NULL,
  `finished` datetime DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

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
  `time_spot1` int(11) DEFAULT NULL,
  `time_spot2` int(11) DEFAULT NULL,
  `time_spot3` int(11) DEFAULT NULL,
  `spot_on` int(11) DEFAULT NULL,
  `refill_trigger` int(11) DEFAULT NULL,
  `refill_max` int(11) DEFAULT NULL,
  `refill_min` int(11) DEFAULT NULL,
  `camera1` int(11) DEFAULT NULL,
  `camera2` int(11) DEFAULT NULL,
  `camera3` int(11) DEFAULT NULL,
  `camera4` int(11) DEFAULT NULL,
  `camera5` int(11) DEFAULT NULL,
  `notify_active` tinyint(1) DEFAULT NULL,
  `notify_time` tinyint(1) DEFAULT NULL,
  `emergency_active` int(11) DEFAULT NULL,
  PRIMARY KEY (`no`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-06-21 22:47:11
