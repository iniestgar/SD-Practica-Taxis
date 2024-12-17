CREATE DATABASE  IF NOT EXISTS `sd_mysql` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `sd_mysql`;
-- MySQL dump 10.13  Distrib 8.0.40, for Win64 (x86_64)
--
-- Host: localhost    Database: sd_mysql
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `taxis`
--

DROP TABLE IF EXISTS `taxis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `taxis` (
  `id_taxi` varchar(10) NOT NULL,
  `token` varchar(255) DEFAULT NULL,
  `nombre` varchar(255) DEFAULT NULL,
  `ciudad` varchar(255) DEFAULT NULL,
  `ocupado` tinyint(1) DEFAULT '0',
  `incidencia` tinyint(1) DEFAULT '0',
  `coordenada_x` int DEFAULT '1',
  `coordenada_y` int DEFAULT '1',
  `cliente_asignado` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_taxi`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `taxis`
--

LOCK TABLES `taxis` WRITE;
/*!40000 ALTER TABLE `taxis` DISABLE KEYS */;
INSERT INTO `taxis` VALUES ('1000',NULL,'jaja','fefe',0,1,1,1,NULL),('1000A',NULL,'hyundai','Valencia',0,1,1,1,NULL),('1001a',NULL,'a','s',0,1,1,1,NULL),('111','znAwpRkmwI','2','2',1,1,2,3,'LW8RQH'),('121','xkV5WbtLrh','2','2',0,0,17,16,'HBQLED'),('12121',NULL,'1','2',0,1,1,1,NULL),('1600cv','SKV1o6ChGB','honda civic','alicnate',0,1,1,1,NULL),('1831982','u8WPRijbUv','23','32',0,1,1,1,NULL),('2000',NULL,'ds','ds',0,1,1,1,NULL),('2000a',NULL,NULL,NULL,0,1,1,1,NULL),('2020','Akf9ofREzz','lol','lel',0,1,1,1,NULL),('21','VxzkqJSNZ7','2','2',0,1,1,1,NULL),('21112','vf9iJBALxY','2','2',0,1,1,1,NULL),('212','pR2xyBS0a6','23','32',0,1,17,16,NULL),('2121212','K11Ab5Tstv','2','2',0,0,17,16,'D7NU7X'),('222','ItR10nHQZ0','2','1',0,1,1,1,NULL),('2222','ls4xslJ7zo','2','2',1,0,9,15,'6487HG'),('2300',NULL,'njnj','nlnl',0,1,1,1,NULL),('2312','cgMjpJP5V1','32','23',0,1,17,16,'MWK2F9'),('231312','yIjeBOZjyV','32','23',0,1,1,1,NULL),('2313131','I0cdBYD5Vp','2','3',0,1,1,1,NULL),('232','pYy2FRAiHi','32','23',0,1,1,1,NULL),('23223',NULL,'2','2',0,1,1,1,NULL),('2323','Xd9VrmqD74','43','43',0,1,1,1,NULL),('23232','kHNKhYYrOd','kia','ytk',0,1,1,1,NULL),('23232323','TRv3qkXXq9','kia','ponte',0,1,1,1,NULL),('234','9NP2vjpDq7','23','32',0,0,17,16,'3V88NI'),('23424','DtxiYyLhP0','4','3',0,1,1,1,NULL),('2399',NULL,'kia','kyoto',0,1,1,1,NULL),('24',NULL,'32','32',0,1,1,1,NULL),('2702','2S2kQLvbIy','toyota','Alicante',0,1,17,16,'QD4EF1'),('27q','27f23250-8fe5-4e4a-a758-18a5a8f52248','Opel','Madrid',0,1,1,1,NULL),('3000a',NULL,'jiji','jeje',0,1,1,1,NULL),('3232','Dku3uuj4TD','23','32',0,1,1,1,NULL),('323232','Xi5Lhp2gYr','2','2',1,1,17,14,'KO8ZE2'),('3232323','MOJVG5SCQF','2','2',1,0,8,17,'XK2D49'),('323232323','n7VzQyMpYK','2','2',1,1,7,7,'A9YGR2'),('32z','c5aa8e1c-4303-45d4-962d-53a0a60d4166','alfa romeo','barcelona',0,1,1,1,NULL),('3300','YXMLZXf5nG','4s','2w',0,1,1,1,NULL),('34','gCLD6C7CIA','e','e',1,0,11,7,'JEQCOU'),('34234','m9EeO4vUml','34','43',0,1,1,1,NULL),('3500','2pKfPAKf9R','jisx','ajs',0,1,1,1,NULL),('4000',NULL,'eh','eh',0,1,1,1,NULL),('4000b',NULL,'byd','kyoto',0,1,1,1,NULL),('44c','a9528288-6000-4c61-bd54-27b209e19ae1',NULL,NULL,0,1,1,1,NULL),('4500','ARVMKRgmRr','23','32',0,1,17,16,'FY8OZ6'),('454',NULL,'2','1',0,1,1,1,NULL),('45z','8ce89650-2cbf-4c7c-a9bf-280a2b062785',NULL,NULL,0,1,1,1,NULL),('4600','t48Nbvzqc5','3f','3t',0,1,1,1,NULL),('5000a',NULL,'jeep','huelva',0,1,1,1,NULL),('54',NULL,'ui','iu',0,1,1,1,NULL),('5600','f8HVSk0lyE','kia','lugo',0,1,1,1,NULL),('5620',NULL,'23','23',0,1,1,1,NULL),('565','QNkW8hFIlF','er','re',0,1,1,1,NULL),('5700',NULL,'3s','svdr',0,1,1,1,NULL),('64i','f1d71871-1c15-4000-80f5-271740212013',NULL,NULL,0,1,1,1,NULL),('65h','eef87c5d-6a7a-49f0-be2a-13457e174333','i','p',0,1,1,1,NULL),('6700','hErKI3eY6R','kia','huelva',0,1,1,1,NULL),('6730','KqWBKgsPJW','toyota','kyoto',0,1,1,1,NULL),('7000','i0YRWuIEqk','ju','je',0,1,1,1,NULL),('72382','6MhJ4akwN2','2','1',0,1,17,16,'KISUDH'),('7878',NULL,'kia','lugo',0,1,1,1,NULL),('7890','UjKIK1b9PF','Kia sport','Alicante',0,1,1,1,NULL),('7892','sBnIdcJ8F1','2','2',1,0,8,12,'2YAYD6'),('78f','0ab5384d-aa3e-4cf8-b0ae-516be611e3a7','e','e',0,1,1,1,NULL),('800','Oas1dxlpPk','kia','alicante',0,1,1,1,NULL),('8000',NULL,'iqsn','xqxb',0,1,1,1,NULL),('8200','CnzAozoeaM','2s','washington',0,1,1,1,NULL),('8292','jTwvT9yO3x','23','23',0,1,1,1,NULL),('890','6VnP3im9sX','23','32',0,1,1,1,NULL),('8902','jRE3MGjCpo','23','32',0,1,17,16,'K2B3XS'),('8920','kYw9bO2O3U','21','23',0,1,1,1,NULL),('8930','3LQR1IMm8g','23','32',0,0,17,16,'O9J8EG'),('900','CKKDEnfdLO','5','8',0,0,17,16,'TQ4YOS'),('90202','QqnJrShBWI','23','32',1,1,19,16,'584VQ7'),('9090',NULL,'4s','2w',0,1,1,1,NULL),('9200','iZ0CSgeFSc','2','2',1,0,2,1,'04GZE9'),('98k','5e7d0cb7-e5ba-4ecc-a009-0afa63800be9','Hyunda','tokyo',0,1,1,1,NULL),('a',NULL,'a','a',0,1,1,1,NULL),('djad',NULL,'asdnka','ak',0,1,1,1,NULL),('h',NULL,NULL,NULL,0,1,1,1,NULL);
/*!40000 ALTER TABLE `taxis` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `idUsuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(25) DEFAULT NULL,
  `ciudad` varchar(25) DEFAULT NULL,
  `correo` varchar(25) DEFAULT NULL,
  PRIMARY KEY (`idUsuario`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'María López','Alicante','mlopez@miempresa.es'),(2,'Juan Fernández','Alicante','jfernandez@miempresa.es'),(3,'Lucía Martínez','Madrid','lmartinez@miempresa.es'),(4,'José Luis\nGutiérrez','Alicante','jgutierrez@miempresa.es'),(5,NULL,NULL,NULL),(6,NULL,NULL,NULL),(7,'Carlos García','Madrid','carlos.garcia@example.com'),(8,'Carlos García','Madrid','carlos.garcia@example.com'),(9,'Carlos García','Madrid','carlos.garcia@example.com');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-17 15:27:37
